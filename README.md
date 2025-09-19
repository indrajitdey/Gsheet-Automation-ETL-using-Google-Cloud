📊 Google Sheets → GCS (Parquet) → BigQuery Automation

This project automates the process of extracting data from Google Sheets, storing it as Parquet files in Google Cloud Storage (GCS), and then loading it into BigQuery.
It ensures incremental loading by tracking the last processed row to avoid duplicates.

🚀 Features

✅ Reads data directly from Google Sheets using the Sheets API

✅ Cleans and normalizes column names for BigQuery compatibility

✅ Tracks last processed row to process only new data

✅ Saves new rows as Parquet files (efficient columnar format)

✅ Uploads Parquet files to Google Cloud Storage

✅ Loads the data into BigQuery with schema enforcement

✅ Cloud Function is triggered via Pub/Sub
```
📂 Project Structure
.
├── main.py                # Cloud Function code
├── requirements.txt       # Python dependencies
├── README.md              # Documentation
└── gsheet-to-gbq-XXXX.json # Service account key (not committed to repo)
```
⚙️ Prerequisites

Before deploying, ensure you have:

* A Google Cloud Project with:

  * Cloud Functions enabled

  * Pub/Sub enabled

  * BigQuery enabled

  * Cloud Storage enabled

* A Service Account with the following roles:

  * `BigQuery Data Editor`

  * `Storage Object Admin`

  * `Sheets API Viewer`

* A Google Sheet with structured tabular data

* Python 3.9+ environment (for local testing)

📌 Environment Setup
1. Clone Repository
```
git clone https://github.com/your-username/gsheet-to-bq-automation.git
cd gsheet-to-bq-automation
```
2. Install Dependencies
```
pip install -r requirements.txt
```
3. Set Up Service Account

Download your service account JSON key

Save it as `gsheet-to-gbq-XXXX.json` in the project root (DO NOT commit to GitHub)

4. Enable APIs
```
gcloud services enable sheets.googleapis.com drive.googleapis.com bigquery.googleapis.com storage.googleapis.com
```
🚀 Deployment
1. Create Pub/Sub Topic
```
gcloud pubsub topics create gsheet-trigger
```
2. Deploy Cloud Function
```
gcloud functions deploy gsheet_to_bq \
  --runtime=python310 \
  --trigger-topic=gsheet-trigger \
  --entry-point=hello_pubsub \
  --region=us-central1 \
  --set-env-vars BUCKET_NAME=gsheet-to-gcs,FOLDER_NAME=parquet_files,PROJECT_ID=gsheet-to-gbq,DATASET_ID=gcloudtask,TABLE_NAME=datafromgsheet
```
⚡ How It Works

1. Trigger: Pub/Sub message activates the Cloud Function.

2. Extract: Function reads new rows from Google Sheets.

3. Transform: Cleans column names & enforces schema.

4. Load: Saves new rows as Parquet → Uploads to GCS → Loads into BigQuery.

5. Track: Updates last processed row in GCS JSON file.

🛠️ Configuration

* BUCKET_NAME: GCS bucket name (stores Parquet + last row file)

* FOLDER_NAME: Subfolder for Parquet files

* PROJECT_ID: Google Cloud project ID

* DATASET_ID: BigQuery dataset name

* TABLE_NAME: BigQuery table name

🧪 Local Testing

To test locally:
```
functions-framework --target=hello_pubsub --debug
```

Then send a Pub/Sub event:
```
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{"message": {"data": "dGVzdA=="}}'
```
📊 Example Workflow

* Google Sheet has 100 rows

* First run: all 100 rows processed → saved in BigQuery

* New rows added (101–120)

* Next run: only 20 new rows processed

🔒 Security

* Never commit service account keys

* Use Secret Manager instead of storing JSON locally

* Apply least privilege principle to service accounts

📝 License

This project is licensed under the MIT License.
