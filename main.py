import base64
import functions_framework
import gspread
import pandas as pd
import json
import datetime
import re
from google.oauth2.service_account import Credentials
from google.cloud import bigquery, storage

# Constants
BUCKET_NAME = "gsheet-to-gcs"
FOLDER_NAME = "parquet_files"
PROJECT_ID = "gsheet-to-gbq"
DATASET_ID = "gcloudtask"
TABLE_NAME = "datafromgsheet"
LAST_ROW_FILE = "last_processed_row.json"  # Stores last processed row index

# ✅ Function to get the last processed row count
def get_last_processed_row(storage_client):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(LAST_ROW_FILE)
    if blob.exists():
        try:
            row_data = json.loads(blob.download_as_text())
            return row_data.get("last_processed_row", 0)  # Default: 0 rows
        except json.JSONDecodeError:
            print("⚠️ Row count file is corrupted. Resetting.")
            return 0
    return 0  # First-time run

# ✅ Function to update last processed row count
def update_last_processed_row(storage_client, row_count):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(LAST_ROW_FILE)
    blob.upload_from_string(json.dumps({"last_processed_row": row_count}))
    print(f"✅ Last processed row count updated: {row_count}")

# ✅ Cloud Function Trigger
@functions_framework.cloud_event
def hello_pubsub(cloud_event):
    print(base64.b64decode(cloud_event.data["message"]["data"]))

    # Google Sheets Authentication
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(
        "gsheet-to-gbq-971523a8b943.json", scopes=SCOPES
    )
    client = gspread.authorize(creds)

    try:
        # Open Google Sheet
        spreadsheet = client.open_by_url(
            "https://docs.google.com/spreadsheets/d/1qrhCAybB4b5jxz7mr-NgdN8zVTdTn8NDVn8mnIG-SQ4"
        )
        worksheet = spreadsheet.sheet1
        print("✅ Google Sheets connected successfully.")

        # Convert Sheet data to Pandas DataFrame
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        if df.empty:
            print("⚠️ No data found in the Google Sheet.")
            return

        print(f"📊 Loaded {len(df)} rows from Google Sheet.")
    except Exception as e:
        print(f"❌ Error loading data from Google Sheets: {e}")
        return

    # ✅ Clean column names for BigQuery compatibility
    def clean_column_name(name):
        name = name.strip().lower()
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        name = re.sub(r"_+", "_", name)
        return name

    df.columns = [clean_column_name(col) for col in df.columns]

    # ✅ Convert tac column and others to STRING
    for col in df.columns:
        if df[col].dtype in ["int64", "float64"]:
            df[col] = df[col].astype(str)  # Ensure all numeric columns are stored as strings

    # ✅ Get last processed row count
    storage_client = storage.Client()
    last_processed_row = get_last_processed_row(storage_client)

    # ✅ Find new rows based on row index
    if len(df) > last_processed_row:
        df_new = df.iloc[last_processed_row:]  # Select only new rows
    else:
        print("✅ No new rows to process. Exiting.")
        return

    print(f"📌 New rows detected: {len(df_new)}")

    # ✅ Update last processed row count
    latest_row_count = len(df)
    update_last_processed_row(storage_client, latest_row_count)

    # ✅ Save only new rows as a Parquet file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    parquet_file_name = f"{FOLDER_NAME}/gsheet_data_{timestamp}.parquet"
    local_parquet_file = f"/tmp/{parquet_file_name.split('/')[-1]}"

    try:
        df_new.to_parquet(local_parquet_file, engine="pyarrow")
        print(f"📂 Data saved locally as Parquet: {local_parquet_file}")
    except Exception as e:
        print(f"❌ Error saving Parquet file locally: {e}")
        return

    # ✅ Upload only new rows as Parquet file to Google Cloud Storage
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(parquet_file_name)
        blob.upload_from_filename(local_parquet_file)
        print(f"✅ Parquet file uploaded to GCS: gs://{BUCKET_NAME}/{parquet_file_name}")
    except Exception as e:
        print(f"❌ Error uploading Parquet file to GCS: {e}")
        return

    # ✅ Load only new rows into BigQuery
    bq_client = bigquery.Client()
    full_table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_NAME}"
    print(f"📌 Loading data into BigQuery Table: {full_table_id}")

    try:
        # ✅ Explicit schema definition to prevent type mismatch
        schema = [
            bigquery.SchemaField("tac", "STRING"),  # Ensure tac is always STRING
            # Add other fields as needed:
            # bigquery.SchemaField("column_name", "INTEGER"),
            # bigquery.SchemaField("another_column", "FLOAT"),
        ]

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,  # Append new data
            schema=schema,  # Apply schema explicitly
        )

        load_job = bq_client.load_table_from_uri(
            f"gs://{BUCKET_NAME}/{parquet_file_name}", full_table_id, job_config=job_config
        )
        load_job.result()

        print(f"✅ Data successfully loaded into BigQuery table: {full_table_id}")
    except Exception as e:
        print(f"❌ Error loading data into BigQuery: {e}")
