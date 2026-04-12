# Clinical Trials ETL Pipeline - TrackingHope

Extract, transform, and load clinical trials data from ClinicalTrials.gov to Supabase using Apache Airflow on Google Cloud Composer.

## Overview

This project orchestrates a daily ETL pipeline that:

1. **Extracts** clinical trial data from ClinicalTrials.gov API for 10 diseases
2. **Transforms** and cleans the data (remove duplicates, standardize formats, etc.)
3. **Loads** the processed data into Supabase PostgreSQL database

The pipeline is fully automated and runs daily at **11:00 AM UTC (Monday-Friday)** via Apache Airflow.

---

## Data Coverage

**10 Diseases Tracked:**
- Hypertension
- Stroke
- COPD
- Tuberculosis
- Malaria
- Diabetes
- Major Depressive Disorder
- Ehlers-Danlos Syndrome
- Lung Cancer
- Ischemic Heart Disease

**Data per Trial:**
- Trial identification (NCTId, Title, Status)
- Design info (Phase, Primary Purpose, Enrollment)
- Results status and sponsorship details
- Locations, conditions, and interventions
- Dates (start, completion, primary completion)
- Summaries, descriptions, and outcomes

**Total Records:** 15,810+ clinical trials

---

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system design.

**Quick Overview:**
```
GitHub (Source Code)
    ↓
GitHub Actions (CI/CD)
    ↓
Google Cloud Composer (Airflow)
    ↓
ClinicalTrials.gov API
    ↓
Supabase PostgreSQL (Data Storage)
```

---

## Prerequisites

- Google Cloud Account with billing enabled
- Supabase account with PostgreSQL database
- GitHub repository (this one!)
- Git CLI installed locally

---

## 🔧 Setup Instructions

### 1. Create Supabase Table

Run this SQL in Supabase SQL Editor:

```sql
CREATE TABLE clinical_trials_combined (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  disease VARCHAR(255),
  nctid VARCHAR(255) UNIQUE NOT NULL,
  title TEXT,
  status VARCHAR(255),
  phase VARCHAR(255),
  primarypurpose VARCHAR(255),
  enrollment INTEGER,
  hasresults BOOLEAN,
  sponsortype VARCHAR(255),
  isfdaregulated BOOLEAN,
  locations TEXT,
  conditions TEXT,
  interventionname TEXT,
  startdate VARCHAR(255),
  enddate VARCHAR(255),
  briefsummary TEXT,
  detaileddescription TEXT,
  keywords TEXT,
  primaryoutcomes TEXT,
  secondaryoutcomes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_nctid ON clinical_trials_combined(nctid);
CREATE INDEX idx_disease ON clinical_trials_combined(disease);
CREATE INDEX idx_phase ON clinical_trials_combined(phase);
```

### 2. Create Cloud Composer Environment

```bash
# Create service account
gcloud iam service-accounts create composer-sa \
  --display-name="Cloud Composer Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:composer-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/composer.worker

# Create Composer environment
gcloud composer environments create tracking-hope-airflow \
  --location us-central1 \
  --service-account=composer-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 3. Configure Credentials

```bash
gcloud composer environments update tracking-hope-airflow \
  --location us-central1 \
  --update-env-variables \
  SUPABASE_URL=YOUR_SUPABASE_URL,SUPABASE_KEY=YOUR_SUPABASE_ANON_KEY
```

### 4. Setup GitHub Actions

Create a service account for GitHub:

```bash
gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Service Account"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:github-actions-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/composer.admin

gcloud iam service-accounts keys create github-key.json \
  --iam-account=github-actions-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

Add the JSON key to GitHub Secrets as `GCP_SA_KEY`.

---

## Project Structure

```
clinical-trials-etl/
├── dags/
│   └── etl_dag.py              # Airflow DAG with complete ETL logic
├── .github/
│   └── workflows/
│       └── deploy-dag.yml       # GitHub Actions deployment workflow
├── README.md                    # This file
├── ARCHITECTURE.md              # Detailed system design
└── requirements.txt             # Python dependencies (minimal)
```

---

## How It Works

### Automatic Execution

The DAG runs automatically every weekday (Monday-Friday) at **11:00 AM UTC**:

1. **Extract Phase** (~3-5 min)
   - Query ClinicalTrials.gov API for each disease
   - Paginate through results
   - Extract 20+ fields per trial

2. **Transform Phase** (~1-2 min)
   - Remove duplicates
   - Standardize phases (Phase 1, 2, 3, 4)
   - Clean text fields
   - Fill missing values

3. **Load Phase** (~2-3 min)
   - Truncate existing table
   - Batch insert 200 records at a time
   - Upsert to handle re-runs

### Manual Trigger

Run manually via Airflow UI:
1. Go to Cloud Composer environment URL
2. Find "clinical_trials_etl_pipeline" DAG
3. Click the play button to trigger

---

## Deployment

### Automatic via GitHub Actions

Every push to the `dags/` folder automatically:
1. Deploys the updated DAG to Cloud Composer
2. Airflow detects and parses the new DAG
3. Pipeline is ready to run on next schedule

### Manual Upload

If needed:
```bash
gcloud composer environments storage dags import \
  --environment=tracking-hope-airflow \
  --location=us-central1 \
  --source=dags/etl_dag.py
```

---

## Monitoring

### View DAG Status
1. Open Cloud Composer environment URL
2. Click "DAGs" tab
3. Find "clinical_trials_etl_pipeline"
4. Check execution history and logs

### View Logs
```bash
gcloud composer environments run tracking-hope-airflow \
  --location us-central1 dags list
```

### Check Supabase Data
1. Go to Supabase dashboard
2. Table Editor → clinical_trials_combined
3. Verify row count and recent inserts

---

## Maintenance

### Update the DAG

1. Modify `dags/etl_dag.py` locally
2. Push to GitHub
3. GitHub Actions automatically deploys
4. Airflow detects changes within 5 minutes

### Add New Disease

Edit `DISEASES` dictionary in `dags/etl_dag.py`:

```python
DISEASES = {
    ...
    'New_Disease': 'Disease Name OR Alternative Name',
}
```

Commit and push - GitHub Actions handles deployment!

### Troubleshooting

**DAG Import Errors:**
- Check Airflow logs in Cloud Composer
- Verify Python syntax with `python -m py_compile dags/etl_dag.py`
- Check environment variables are set

**Data Not Loading:**
- Verify Supabase credentials
- Check table exists and has correct schema
- View execution logs in Airflow UI

**Pipeline Timeout:**
- Increase `execution_timeout` in DAG
- Check ClinicalTrials.gov API status
- Monitor network connectivity

---

## Performance

- **Execution Time:** 5-10 minutes per run
- **Records Processed:** 15,810+ per day
- **API Rate Limit:** ~0.5 second delay between requests
- **Batch Size:** 200 records per database insert
- **Cost:** ~$0-5/month (within GCP free tier)

---

## Team

- **Zina Tiar**
- **Matthias Haeflinger**
- **Ziad Bejaoui**

---

## 📄 License

MIT

---

## Support

For issues or questions:
1. Check [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
2. Review Airflow logs in Cloud Composer UI
3. Open an issue on GitHub
4. Check Supabase documentation for database issues

---

## Next Steps

- [ ] Build visualization dashboard (Dash/Streamlit)
- [ ] Add data quality checks as DAG task
- [ ] Setup email alerts for failed runs
- [ ] Add historical data backfill capability
- [ ] Implement incremental loading (append-only mode)

---

**Last Updated:** April 12, 2026  
**Airflow Version:** 2.10.5  
**Composer Version:** 3
