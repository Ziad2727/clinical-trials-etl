# Google Cloud Deployment Guide

## Prerequisites

1. Google Cloud Account (free tier available)
2. gcloud CLI installed: https://cloud.google.com/sdk/docs/install
3. Project created in Google Cloud Console
4. Billing enabled (Cloud Functions free tier: 2M invocations/month)

---

## Step 1: Setup gcloud CLI

```bash
gcloud init
gcloud auth login
gcloud config set project clinical-trials-etl
```

---

## Step 2: Enable Required APIs

```bash
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable pubsub.googleapis.com
```

---

## Step 3: Create Pub/Sub Topics

```bash
gcloud pubsub topics create clinical-trials-trigger
gcloud pubsub topics create clinical-trials-summaries-trigger
```

---

## Step 4: Deploy ETL Trials Function

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

---

## Step 5: Deploy ETL Summaries Function

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

---

## Step 6: Create Cloud Scheduler Jobs

### For Trials (Monday-Friday 10:00 AM UTC)

```bash
gcloud scheduler jobs create pubsub etl-trials-daily \
  --schedule="0 10 * * 1-5" \
  --topic=clinical-trials-trigger \
  --message-body="{}" \
  --time-zone="UTC"
```

### For Summaries (Monday-Friday 11:00 AM UTC)

```bash
gcloud scheduler jobs create pubsub etl-summaries-daily \
  --schedule="0 11 * * 1-5" \
  --topic=clinical-trials-summaries-trigger \
  --message-body="{}" \
  --time-zone="UTC"
```

---

## Step 7: Verify Deployment

### Check Functions
```bash
gcloud functions list
```

### Check Scheduler Jobs
```bash
gcloud scheduler jobs list
```

### View Logs
```bash
gcloud functions logs read etl_trials --limit 50
gcloud functions logs read etl_summaries --limit 50
```

---

## Step 8: Manual Testing

### Test Trials Function
```bash
gcloud functions call etl_trials --data '{}'
```

### Test Summaries Function
```bash
gcloud functions call etl_summaries --data '{}'
```

---

## Monitoring in Google Cloud Console

1. Go to https://console.cloud.google.com
2. Navigate to **Cloud Functions**
3. Click on function name
4. Click **Logs** tab
5. Filter by timestamp

---

## Troubleshooting

### Function Fails to Deploy

**Error**: "Missing dependencies"
```bash
# Make sure requirements.txt is in same directory as main.py and summaries.py
```

**Error**: "Timeout exceeded"
```bash
# Increase timeout (max 540 seconds):
gcloud functions deploy etl_trials --timeout 540 ...
```

### Function Runs But No Data

1. Check environment variables are set correctly
2. Verify Supabase tables exist
3. Check if API is returning data:
   - Visit: https://clinicaltrials.gov/api/v2/studies
   - Add filters: ?query.cond=Hypertension&pageSize=10

### High Execution Time

- Reduce number of diseases (edit DISEASES dict in code)
- Increase memory: --memory 1024MB
- Check API rate limits

---

## Cost Estimation

**Free Tier** (per month):
- 2,000,000 function invocations
- 400,000 GB-seconds of compute time
- Scheduler: 3 jobs free

**Estimated Usage** (with daily runs):
- 60 invocations/month (2 functions × 30 days)
- ~300 GB-seconds/month (5 min × 1GB memory × 60 runs)

**Total Cost**: ~$0 (within free tier)

---

## Update Code

To update code after pushing to GitHub:

```bash
# Pull latest from GitHub
git pull origin main

# Redeploy
gcloud functions deploy etl_trials --source .
gcloud functions deploy etl_summaries --source .
```

---

## Rollback to Previous Version

```bash
# List previous deployments
gcloud functions describe etl_trials

# Or manually redeploy from git tag
git checkout <tag>
gcloud functions deploy etl_trials --source .
```