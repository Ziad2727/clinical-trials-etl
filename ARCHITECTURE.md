# Architecture - Clinical Trials ETL Pipeline

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Developer Workflow                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Local Machine (Git)                                            │
│         ↓                                                        │
│  git push → GitHub Repository                                   │
│         ↓                                                        │
│  GitHub Actions (CI/CD)                                         │
│    ├─ Authenticate to GCP                                       │
│    ├─ Upload DAG to Cloud Composer                              │
│    └─ Verify upload                                             │
│         ↓                                                        │
│  Google Cloud Composer (Airflow 2.10.5)                         │
│         ↓                                                        │
│  Scheduler triggers DAG (lun-ven 11:00 UTC)                     │
│         ↓                                                        │
│  Worker executes: extract → transform → load                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Architecture

```
┌──────────────────────────┐
│  ClinicalTrials.gov API  │  ← Source of truth for clinical trials
└────────────┬─────────────┘
             │
             ↓
    ┌────────────────────┐
    │  Extract Phase     │
    │                    │
    │ • Query API        │
    │ • Paginate results │
    │ • Get 20+ fields   │
    │ • Handle 10 disease│
    │   searches         │
    └────────┬───────────┘
             │
             ↓
    ┌────────────────────┐
    │  Transform Phase   │
    │                    │
    │ • Remove dups      │
    │ • Standardize      │
    │   phases           │
    │ • Clean text       │
    │ • Fill NAs         │
    └────────┬───────────┘
             │
             ↓
    ┌────────────────────┐
    │  Load Phase        │
    │                    │
    │ • Batch 200        │
    │   records          │
    │ • Truncate old     │
    │ • HTTP POST to     │
    │   Supabase         │
    └────────┬───────────┘
             │
             ↓
    ┌──────────────────────────┐
    │  Supabase PostgreSQL     │  ← Final storage
    │  (15,810+ trials)        │
    └──────────────────────────┘
```

---

## Component Details

### 1. GitHub Repository

**Role:** Source of truth for code and configuration

**Structure:**
```
clinical-trials-etl/
├── dags/
│   └── etl_dag.py              # Complete DAG definition
├── .github/
│   └── workflows/
│       └── deploy-dag.yml       # Automated deployment
├── README.md                    # User documentation
├── ARCHITECTURE.md              # This file
└── requirements.txt             # Python deps (requests only)
```

**Key Files:**
- `dags/etl_dag.py` (1200+ lines): All extraction, transformation, loading logic
- `deploy-dag.yml`: GitHub Actions workflow for automated deployment

---

### 2. GitHub Actions Workflow

**Trigger:** Any push to `main` branch where `dags/` changes

**Workflow Steps:**

```yaml
1. Checkout code
   └─ Clone the repository
   
2. Authenticate to Google Cloud
   └─ Uses GCP_SA_KEY secret
   
3. Setup Cloud SDK
   └─ Configure gcloud CLI
   
4. Upload DAG to Cloud Composer
   └─ gcloud composer environments storage dags import
   
5. Verify upload
   └─ gcloud composer environments storage dags list
```

**Duration:** ~2-3 minutes

**Error Handling:**
- Workflow fails if any step fails
- GitHub shows red ✗ if deployment unsuccessful
- Cloud Composer shows "DAG Import Errors" if syntax issues

---

### 3. Google Cloud Composer (Airflow)

**Type:** Managed Apache Airflow service on GCP

**Configuration:**
- **Version:** Composer 3 (Airflow 2.10.5)
- **Environment:** tracking-hope-airflow
- **Location:** us-central1
- **Size:** Small (suitable for daily runs)

**Components:**

```
Cloud Composer Environment
├── Airflow Webserver
│   └─ UI for monitoring DAGs
│       (https://1258ba9f...composer.googleusercontent.com)
│
├── Airflow Scheduler
│   └─ Triggers DAG at scheduled times
│       (every Mon-Fri 11:00 UTC)
│
├── Airflow Worker(s)
│   └─ Execute actual ETL code
│       (extract, transform, load)
│
├── PostgreSQL Metadata DB
│   └─ Stores DAG runs, logs, state
│
├── GCS Bucket
│   └─ Stores DAGs and logs
│       (gs://us-central1-tracking-hope-a-76f903b6-bucket/)
│
└── Environment Variables
    ├─ SUPABASE_URL
    └─ SUPABASE_KEY
```

**DAG Schedule:**
```
schedule_interval='0 11 * * 1-5'
                   │  │  │  │  └─ Day of week (1-5 = Mon-Fri)
                   │  │  │  └──── Month (*)
                   │  │  └─────── Day of month (*)
                   │  └────────── Hour (11 UTC)
                   └───────────── Minute (0)
```

---

### 4. Airflow DAG: clinical_trials_etl_pipeline

**Type:** Python DAG with single PythonOperator task

**Task:** `run_clinical_trials_etl`

**Execution Logic:**

```python
def run_etl():
    1. Load Supabase credentials from env vars
    
    2. For each of 10 diseases:
       a. Query ClinicalTrials.gov API
       b. Paginate through results
       c. Extract trial information
       d. Handle pagination (up to 15,000+ results)
       e. Combine into DataFrame
    
    3. Transform data:
       a. Remove duplicates by NCTId
       b. Filter valid phases only
       c. Clean text fields (remove \n, \r)
       d. Fill N/A values
    
    4. Load to Supabase:
       a. Truncate old table
       b. Batch insert 200 records at a time
       c. Use HTTP REST API (no external lib needed)
    
    5. Log all progress and completion
```

**Retry Logic:**
- Max retries: 3
- Retry delay: 5 minutes
- Timeout: 15 minutes per execution

**Error Handling:**
- All exceptions logged with timestamps
- DAG fails if critical error occurs
- Airflow UI shows failure status
- Partial data loading handled gracefully

---

### 5. ClinicalTrials.gov API

**Endpoint:** `https://clinicaltrials.gov/api/v2/studies`

**Rate Limiting:**
- 0.5 second delay between paginated requests
- Prevents overwhelming the API

**Query Pattern:**
```
GET /api/v2/studies?
  query.cond=Disease+Name
  &filter.overallStatus=RECRUITING,...
  &pageSize=1000
  &pageToken=<next_page>
```

**Fields Extracted (20+):**
```
Basic Info:
  - nctid (unique identifier)
  - title
  - status (RECRUITING, COMPLETED, etc.)

Design:
  - phase (Phase 1, 2, 3, 4)
  - primarypurpose (TREATMENT, PREVENTION, etc.)
  - enrollment (number of participants)

Sponsorship:
  - sponsortype (INDUSTRY, ACADEMIC, etc.)
  - isfdaregulated (boolean)

Locations & Conditions:
  - locations (countries)
  - conditions (medical conditions)
  - interventionname (drugs/treatments)

Timeline:
  - startdate
  - enddate
  - primarycompletiondate

Summaries & Outcomes:
  - briefsummary
  - detaileddescription
  - keywords
  - primaryoutcomes
  - secondaryoutcomes

Results:
  - hasresults (whether results published)
```

---

### 6. Supabase PostgreSQL

**Role:** Data warehouse for all clinical trials

**Table:** `clinical_trials_combined`

**Schema:**
```sql
id BIGINT PRIMARY KEY (auto-generated)
disease VARCHAR(255)          -- Which disease category
nctid VARCHAR(255) UNIQUE     -- Trial identifier
title TEXT                    -- Trial title
status VARCHAR(255)           -- Current status
phase VARCHAR(255)            -- Trial phase
primarypurpose VARCHAR(255)   -- TREATMENT, PREVENTION, etc.
enrollment INTEGER            -- Participant count
hasresults BOOLEAN            -- Results published?
sponsortype VARCHAR(255)      -- INDUSTRY, ACADEMIC, etc.
isfdaregulated BOOLEAN        -- FDA regulated?
locations TEXT                -- Countries
conditions TEXT               -- Medical conditions
interventionname TEXT         -- Drugs/treatments
startdate VARCHAR(255)        -- Start date
enddate VARCHAR(255)          -- Completion date
briefsummary TEXT             -- Brief description
detaileddescription TEXT      -- Detailed description
keywords TEXT                 -- Associated keywords
primaryoutcomes TEXT          -- Primary measurements
secondaryoutcomes TEXT        -- Secondary measurements
created_at TIMESTAMP          -- Record creation time

INDEXES:
- idx_nctid ON nctid         -- Fast lookups by trial ID
- idx_disease ON disease     -- Fast filtering by disease
- idx_phase ON phase         -- Fast filtering by phase
```

**Data Storage:**
- ~15,810 clinical trials
- ~25 KB per record (average)
- ~400 MB total storage (within free tier)

**Load Method:**
- HTTP REST API (Supabase PostgREST)
- Batch inserts: 200 records per request
- Total insert time: ~2-3 minutes

---

## Security

### Credentials Management

**Supabase Credentials:**
- Stored in Cloud Composer environment variables
- Not in code or GitHub
- Uses public API key (anon) - safe for public API calls
- Row-Level Security (RLS) policies can restrict access

**GitHub Actions:**
- Service account credentials stored as GitHub Secret
- Only accessible during GitHub Actions execution
- Not logged or exposed

**Service Accounts:**
```
composer-sa@clinical-trials-etl.iam.gserviceaccount.com
  └─ Used by Cloud Composer
  └─ Roles: composer.worker

github-actions-sa@clinical-trials-etl.iam.gserviceaccount.com
  └─ Used by GitHub Actions
  └─ Roles: composer.admin
```

---

## Cost Estimation

### Google Cloud (Monthly)

| Service | Usage | Cost |
|---------|-------|------|
| Cloud Composer | ~30 invocations/month | ~$0-5 |
| Cloud Logging | ~500 MB logs | ~$0 (free tier) |
| Cloud Storage | ~50 GB bucket | ~$0 (free tier) |
| **Total** | | **~$0-5/month** |

### Supabase (Monthly)

| Item | Usage | Cost |
|------|-------|------|
| Storage | ~400 MB | ~$0 (free tier) |
| API Requests | ~500K/month | ~$0 (free tier) |
| **Total** | | **~$0/month** |

**Total Cost:** ~$0-5/month (within free tier)

---

## Performance Metrics

### Execution Timeline

| Phase | Duration | Notes |
|-------|----------|-------|
| API Extraction | 3-5 min | Paginating through 10 diseases |
| Data Transform | 1-2 min | Dedup, clean, filter |
| Database Load | 2-3 min | Batching 200 records per insert |
| **Total** | 6-10 min | Per execution |

### Data Volume

| Metric | Value |
|--------|-------|
| Total Trials | 15,810 |
| Per Disease | 1,000-3,000 |
| Fields per Trial | 20+ |
| Batch Size | 200 records |
| Insert Batches | ~79 batches |

### API Performance

| Metric | Value |
|--------|-------|
| ClinicalTrials.gov Requests | ~30 requests |
| Response Time | 500-1000ms avg |
| Rate Limit Delay | 0.5 seconds |
| Pagination Depth | ~3-10 pages/disease |

---

## Deployment Flow

### Initial Setup (One-time)

```
1. Create GCP Project
2. Enable APIs (Composer, IAM, etc.)
3. Create service accounts + keys
4. Create Cloud Composer environment
5. Create Supabase table
6. Add GitHub secrets (GCP_SA_KEY)
7. Push code to GitHub
```

### Recurring Deployment (Per change)

```
1. Developer modifies dags/etl_dag.py
2. git push to GitHub
3. GitHub Actions triggered
4. Workflow:
   a. Authenticate to GCP
   b. Upload DAG to Cloud Composer bucket
   c. Airflow detects change (~5 min)
   d. DAG is ready for next scheduled run
5. No manual intervention needed
```

---

## Monitoring & Observability

### Airflow UI Dashboard

**Access:** Cloud Composer environment URL

**Available Views:**
- DAG Graph (visualization of tasks)
- Tree View (execution history)
- Gantt Chart (execution timeline)
- Log Viewer (real-time logs)

### Log Locations

**Cloud Logging:**
```
Projects → Cloud Composer → Logs
Filter: resource.type="cloud_composer_environment"
```

**Application Logs:**
- Airflow webserver logs
- Scheduler logs
- Worker logs

### Alerting (Optional)

Can be configured:
- Cloud Monitoring alerts on DAG failures
- Email notifications via Airflow
- Slack webhooks for status updates

---

## Disaster Recovery

### Backup Strategy

**Code:**
- GitHub is source of truth
- Automatic backup via git history

**Data:**
- Supabase handles automated backups
- Daily snapshots (configurable)
- Point-in-time recovery available

**DAG State:**
- Airflow metadata stored in Cloud Composer's PostgreSQL
- Automatically managed by Cloud Composer
- Can be exported if needed

### Recovery Procedures

**If DAG fails:**
1. Check Airflow logs for error
2. Fix code issue
3. Push to GitHub
4. GitHub Actions deploys fix
5. Manually trigger DAG in Airflow UI or wait for next schedule

**If data is corrupted:**
1. Verify data integrity in Supabase
2. Check backup/snapshot in Supabase
3. Restore from backup if needed
4. Re-run DAG to reload clean data

---

## Future Enhancements

### Potential Improvements

- [ ] **Incremental Loading** - Append-only mode to preserve history
- [ ] **Data Quality Checks** - Add data validation task
- [ ] **Email Alerts** - Notify on failures
- [ ] **Dynamic Scheduling** - Run on-demand via API
- [ ] **Historical Backfill** - Load older trial data
- [ ] **Visualization Dashboard** - Streamlit/Dash app
- [ ] **Multi-region** - Deploy to multiple regions
- [ ] **Custom Metrics** - Prometheus metrics export

### Scalability Considerations

**If you need to:**
- Add more diseases: Simple dict entry in DISEASES
- Increase frequency: Change `schedule_interval`
- Handle more data: Increase Cloud Composer size
- Add new transformations: Add steps to `run_etl()` function

---

## Documentation References

- [Apache Airflow Docs](https://airflow.apache.org/docs/)
- [Google Cloud Composer Docs](https://cloud.google.com/composer/docs)
- [Supabase API Docs](https://supabase.com/docs/api)
- [ClinicalTrials.gov API Docs](https://clinicaltrials.gov/api/info/about_api)

---

**Last Updated:** April 12, 2026  
**Architecture Version:** 2.0 (Airflow-based)  
**Status:** Production Ready ✅