# Clinical Trials ETL Pipeline

Extraction, transformation, and loading of clinical trials data from ClinicalTrials.gov to Supabase using Google Cloud Functions.

## Overview

This project extracts combined clinical trials data for 10 diseases:
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

## Architecture

```
ClinicalTrials.gov API
        ↓
Google Cloud Functions (Daily execution)
        ↓
Supabase PostgreSQL (Data storage)
        ↓
Dash/R Shiny (Visualization - Future)
```

## Single ETL Function

### **main.py** - Combined Trials and Summaries

Extracts complete trial information combined with summaries:

**Trial Data**:
- NCTId, Title, Status, Phase
- Enrollment, Results Status
- Sponsor Type, FDA Regulation
- Locations, Conditions
- Intervention Names
- Start/End Dates

**Summary Data**:
- Brief Summary
- Detailed Description
- Keywords
- Primary Outcomes
- Secondary Outcomes

**Table**: `clinical_trials_combined` (15,810 records)

## Filters Applied

- **Status**: RECRUITING, ACTIVE_NOT_RECRUITING, ENROLLING_BY_INVITATION, COMPLETED
- **Primary Purpose**: TREATMENT or PREVENTION only
- **Phase**: Phase 1, 2, 3, 4 (Early Phase 1 included)
- **Duplicates**: Removed based on NCTId

## Data Statistics

- **Total Records**: 15,810 (combined trials + summaries)
- **Unique Diseases**: 10
- **Execution Time**: ~5-10 minutes per run
- **Update Frequency**: Daily (Monday-Friday 11:00 AM UTC)

## Prerequisites

- Google Cloud Account (free tier available)
- Supabase Account with PostgreSQL database
- gcloud CLI installed
- Python 3.11+

## Project Structure

```
clinical-trials-etl/
├── main.py                    # Combined ETL function
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── DEPLOYMENT.md              # Detailed deployment guide
├── .gitignore                 # Git ignore rules
└── logs/                      # Log files directory
    └── .gitkeep
```

## Dependencies

```
requests==2.31.0
numpy==1.26.0
pandas==2.1.0
supabase==2.28.3
```

## Deployment to Google Cloud

### Step 1: Setup Google Cloud

```bash
gcloud init
gcloud auth login
gcloud config set project clinical-trials-etl
```

### Step 2: Enable Required APIs

```bash
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable pubsub.googleapis.com
```

### Step 3: Create Pub/Sub Topic

```bash
gcloud pubsub topics create clinical-trials-trigger
```

### Step 4: Create Supabase Table

In Supabase SQL Editor, run:

```sql
CREATE TABLE clinical_trials_combined (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  Disease VARCHAR(255),
  NCTId VARCHAR(255) UNIQUE NOT NULL,
  Title TEXT,
  Status VARCHAR(255),
  Phase VARCHAR(255),
  PrimaryPurpose VARCHAR(255),
  Enrollment INTEGER,
  HasResults BOOLEAN,
  SponsorType VARCHAR(255),
  IsFdaRegulated BOOLEAN,
  Locations TEXT,
  Conditions TEXT,
  InterventionName TEXT,
  StartDate VARCHAR(255),
  EndDate VARCHAR(255),
  BriefSummary TEXT,
  DetailedDescription TEXT,
  Keywords TEXT,
  PrimaryOutcomes TEXT,
  SecondaryOutcomes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_nctid ON clinical_trials_combined(NCTId);
CREATE INDEX idx_disease ON clinical_trials_combined(Disease);
CREATE INDEX idx_phase ON clinical_trials_combined(Phase);
```

### Step 5: Deploy ETL Combined Function

```bash
gcloud functions deploy etl_combined \
  --runtime python3.11 \
  --trigger-topic clinical-trials-trigger \
  --entry-point etl_combined \
  --timeout 540 \
  --memory 512MB \
  --set-env-vars SUPABASE_URL=https://cmvnwgmcbmhpldluycya.supabase.co,SUPABASE_KEY=your_anon_key \
  --source .
```

### Step 6: Create Cloud Scheduler Job

**For Combined ETL (Monday-Friday 11:00 AM UTC)**

```bash
gcloud scheduler jobs create pubsub etl-combined-daily \
  --schedule="0 11 * * 1-5" \
  --location=us-central1 \
  --topic=clinical-trials-trigger \
  --message-body="{}" \
  --time-zone="UTC"
```

## Manual Execution

To manually trigger the ETL pipeline:

```bash
gcloud scheduler jobs run etl-combined-daily --location=us-central1
```

## Monitoring

### View Logs via CLI

```bash
gcloud functions logs read etl_combined --limit 50
```

### View in Cloud Console

1. Go to https://console.cloud.google.com
2. Navigate to **Cloud Functions**
3. Click on **etl_combined**
4. Click **Logs** tab

### View Data in Supabase

1. Go to https://app.supabase.com
2. Select **TrackingHope** project
3. Click **Table Editor**
4. Select **clinical_trials_combined**
5. View 15,810 records

## Local Testing

### Install Dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

### Test ETL Function Locally

```bash
python3 << 'EOF'
from main import etl_combined

# Mock event and context
class Event:
    pass

class Context:
    pass

# Run the function
etl_combined(Event(), Context())
EOF
```

## Troubleshooting

### Function Timeout
- Increase timeout parameter (max 540 seconds)
- Check ClinicalTrials.gov API rate limits
- Review logs for slow API responses

### Database Connection Issues
- Verify Supabase URL and API key
- Check network connectivity
- Ensure `clinical_trials_combined` table exists

### Missing Data
- Check disease search queries in DISEASES dictionary
- Verify filter criteria (status, purpose, phase)
- Review logs for API errors

### Memory Issues
- Increase memory allocation (max 8GB)
- Monitor DataFrame sizes
- Consider pagination improvements

## Cost Estimation

**Free Tier** (per month):
- 2,000,000 function invocations (ample for daily runs)
- 400,000 GB-seconds of compute time
- Cloud Scheduler: 3 jobs free

**Estimated Usage**:
- ~30 invocations/month (daily runs)
- ~150 GB-seconds/month

**Total Cost**: ~$0 (within free tier)

## Data Transformation Steps

1. **Extraction**: Fetch from ClinicalTrials.gov API using disease search queries
2. **Filtering**: Apply status, purpose, and phase filters
3. **Cleaning**: Remove duplicates, fill missing values
4. **Phase Standardization**: Normalize phase naming (Phase 1, Phase 2, etc.)
5. **Text Cleaning**: Remove newlines and extra spaces from summaries
6. **N/A Replacement**: Replace "N/A" with "Not published" in summary fields
7. **Loading**: UPSERT into Supabase `clinical_trials_combined` table

## GitHub Repository

```
https://github.com/Ziad2727/clinical-trials-etl
```

## Next Steps

1. Deploy function to Google Cloud ✅
2. Create Cloud Scheduler job ✅
3. Monitor execution logs ✅
4. Create visualization dashboard (Dash or R Shiny)
5. Share dashboard with stakeholders
6. Setup alerts for failed runs

## Team

Contributors:
- Zina Tiar
- Matthias Haeflinger
- Ziad Bejaoui

## Support

For issues or questions:
1. Check the logs in Google Cloud Console
2. Verify Supabase connectivity
3. Open an issue on GitHub
4. Review DEPLOYMENT.md for detailed troubleshooting

## License

MIT