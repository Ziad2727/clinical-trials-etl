# Clinical Trials ETL Pipeline

Extraction, transformation, and loading of clinical trials data from ClinicalTrials.gov to Supabase using Google Cloud Functions.

## Overview

This project extracts clinical trials data for 10 diseases:
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
Dash/R Shiny (Visualization)
```

## Two ETL Functions

### 1. **main.py** - Clinical Trials Data
Extracts complete trial information:
- NCTId, Title, Status, Phase
- Enrollment, Results Status
- Sponsor Type, FDA Regulation
- Locations, Conditions
- Intervention Names
- Start/End Dates

**Table**: `clinical_trials`

### 2. **summaries.py** - Trial Summaries & Results
Extracts detailed information:
- Brief Summary
- Detailed Description
- Keywords
- Primary Outcomes
- Secondary Outcomes
- Has Results Flag

**Table**: `clinical_trials_summary`

## Filters Applied

- **Status**: RECRUITING, ACTIVE_NOT_RECRUITING, ENROLLING_BY_INVITATION, COMPLETED
- **Primary Purpose**: TREATMENT or PREVENTION only
- **Phase**: Phase 1, 2, 3, 4 (Early Phase 1 included)

## Data Statistics

- **Total Trials**: ~12,830
- **Total Summaries**: ~12,830
- **Execution Time**: ~10-15 minutes per run
- **Update Frequency**: Daily (Monday-Friday 10:00 AM UTC)

## Prerequisites

- Google Cloud Account (free tier available)
- Supabase Account with PostgreSQL database
- gcloud CLI installed
- Python 3.11+

## Deployment to Google Cloud

### Step 1: Setup Google Cloud

```bash
gcloud init
gcloud auth login
gcloud config set project clinical-trials-etl
```

### Step 2: Enable APIs

```bash
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable pubsub.googleapis.com
```

### Step 3: Create Pub/Sub Topics

```bash
gcloud pubsub topics create clinical-trials-trigger
gcloud pubsub topics create clinical-trials-summaries-trigger
```

### Step 4: Deploy ETL Trials Function

```bash
gcloud functions deploy etl_trials \
  --runtime python3.11 \
  --trigger-topic clinical-trials-trigger \
  --entry-point etl_trials \
  --timeout 540 \
  --memory 512MB \
  --set-env-vars SUPABASE_URL=https://cmvnwgmcbmhpdluycya.supabase.co,SUPABASE_KEY=your_anon_key \
  --source .
```

### Step 5: Deploy ETL Summaries Function

```bash
gcloud functions deploy etl_summaries \
  --runtime python3.11 \
  --trigger-topic clinical-trials-summaries-trigger \
  --entry-point etl_summaries \
  --timeout 540 \
  --memory 512MB \
  --set-env-vars SUPABASE_URL=https://cmvnwgmcbmhpdluycya.supabase.co,SUPABASE_KEY=your_anon_key \
  --source .
```

### Step 6: Create Cloud Scheduler Jobs

**For Trials (Monday-Friday 10:00 AM UTC)**

```bash
gcloud scheduler jobs create pubsub etl-trials-daily \
  --schedule="0 10 * * 1-5" \
  --topic=clinical-trials-trigger \
  --message-body="{}" \
  --time-zone="UTC"
```

**For Summaries (Monday-Friday 11:00 AM UTC)**

```bash
gcloud scheduler jobs create pubsub etl-summaries-daily \
  --schedule="0 11 * * 1-5" \
  --topic=clinical-trials-summaries-trigger \
  --message-body="{}" \
  --time-zone="UTC"
```

## Monitoring

### View Logs

```bash
gcloud functions logs read etl_trials --limit 50
gcloud functions logs read etl_summaries --limit 50
```

### View in Cloud Console

1. Go to https://console.cloud.google.com
2. Navigate to **Cloud Functions**
3. Click on function name
4. Click **Logs** tab

## Local Testing

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Test Trials Function

```bash
python3 << 'EOF'
from main import etl_trials

# Mock request object
class Request:
    pass

response = etl_trials(Request())
print(response)
EOF
```

## Troubleshooting

### Function Timeout
- Increase timeout (max 540 seconds)
- Check API rate limits
- Reduce number of diseases if needed

### Database Connection Issues
- Verify Supabase credentials
- Check network connectivity
- Ensure tables exist in Supabase

### Missing Data
- Check filter criteria in code
- Verify disease search queries
- Review logs for API errors

## Cost Estimation

**Free Tier** (per month):
- 2,000,000 function invocations
- 400,000 GB-seconds of compute time
- Scheduler: 3 jobs free

**Estimated Usage**:
- ~60 invocations/month (2 functions × 30 days)
- ~300 GB-seconds/month

**Total Cost**: ~$0 (within free tier)

## Team

Add team members:
- @zina
- @matthias

## Next Steps

1. Deploy functions to Google Cloud
2. Create Cloud Scheduler jobs
3. Monitor execution logs
4. Create visualization (Dash or R Shiny)
5. Share dashboard with stakeholders

## Support

For issues or questions, open an issue on GitHub or contact the team.

## License

MIT