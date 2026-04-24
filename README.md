# Clinical Trials ETL Pipeline - TrackingHope

Extract, transform, and load clinical trials data from ClinicalTrials.gov to Supabase using Apache Airflow on Google Cloud Composer. Includes interactive Dash dashboard with AI chatbot.

## Overview

This project orchestrates a complete clinical trials intelligence platform:

1. **Extracts** clinical trial data from ClinicalTrials.gov API for 10 diseases
2. **Transforms** and cleans the data (remove duplicates, standardize formats, etc.)
3. **Loads** the processed data into Supabase PostgreSQL database
4. **Visualizes** with interactive Dash dashboard and analytics
5. **Chatbot** for answering questions about trials

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

**Total Records:** 
- 57,684 trials extracted
- 20,462 advanced trials (Phase 1-4 + TREATMENT/PREVENTION)
- 220+ countries

---

## Architecture
GitHub (Source Code)
↓
GitHub Actions (CI/CD)
↓
Google Cloud Composer (Airflow)
↓
ClinicalTrials.gov API
↓
Supabase PostgreSQL
↓
Dash Dashboard + Chatbot

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system design.

---

## Prerequisites

- Google Cloud Account with billing enabled
- Supabase account with PostgreSQL database
- GitHub repository (this one!)
- Git CLI installed locally
- Python 3.9+

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
clinical-trials-etl/
├── dags/
│   └── etl_dag.py                    # Airflow DAG with complete ETL logic
├── Projet3 dash V2/
│   ├── app.py                        # Dash main application
│   ├── data.py                       # Supabase data layer + scoring
│   ├── chatbot.py                    # FAQ chatbot logic
│   ├── chatbot_ui.py                 # Chatbot UI component
│   ├── pages/
│   │   ├── welcome.py               # Landing page
│   │   ├── disease.py               # Disease analysis page
│   │   ├── favorites.py             # Saved studies page
│   │   ├── infos.py                 # About page
│   │   ├── login.py                 # Authentication page
│   │   └── settings.py              # User settings
│   ├── translations.py              # Multi-language support (8 languages)
│   ├── assets/
│   │   └── styles.css               # Design system
│   └── requirements.txt
├── .github/
│   └── workflows/
│       └── deploy-dag.yml           # GitHub Actions deployment
├── README.md                        # This file
├── ARCHITECTURE.md                  # Detailed system design
└── requirements.txt                 # Python dependencies

---

## How It Works

### ETL Pipeline

The DAG runs automatically every weekday (Monday-Friday) at **11:00 AM UTC**:

1. **Extract Phase** (~20 min)
   - Query ClinicalTrials.gov API for each disease
   - Paginate through results (1000 per page)
   - Extract 20+ fields per trial

2. **Transform Phase** (~5 min)
   - Remove duplicates by NCTId
   - Standardize phases (PHASE1, PHASE2, PHASE3, PHASE4)
   - Filter by disease keywords in conditions
   - Clean text fields (newlines, extra spaces)
   - Fill missing values with "Unknown"

3. **Load Phase** (~35 min)
   - Truncate existing table
   - Batch insert 200 records at a time
   - Upsert to handle re-runs

**Total Execution Time:** ~60 minutes

### Dashboard Features

**Welcome Page**
- Hero section with disease selector
- Explore button to navigate to disease details

**Disease Page**
- **3 KPIs:** Total Trials | Active Trials | Advanced Trials
- **Phase Distribution:** Bar chart showing Phase I, II, III, IV breakdown
- **Timeline:** Trials started per year since 2010
- **Geographic Map:** World map showing trial locations by country
- **Top 5 Promising Trials:** Scored by Promise Score
- **Data Table:** Sortable table with NCT ID, intervention, phase, enrollment, region, score

**Promise Score Calculation**
Score = Phase (40) + Results (20) + Sponsor (20) + FDA (10) + Enrollment (15)

Phase IV = 40pts, Phase III = 30pts, Phase II = 15pts, Phase I = 0pts
Published Results = 20pts
Industry Sponsor = 20pts
FDA Regulated = 10pts
Enrollment weighted by region (USA/EU = 1.0x, Others = 0.6x)


**Favorites Page**
- Save and manage favorite trials
- Easy access to studies of interest

**Settings**
- Language selector (8 languages: EN, FR, ES, DE, IT, ZH, AR, PT)
- Dark mode toggle
- Logout

### Chatbot Features

10 pre-defined FAQ questions accessible via floating widget:

1. How many Phase 3 trials?
2. Which pharmaceutical sponsors?
3. How many published results?
4. What's the average enrollment?
5. Which drugs are being tested?
6. In how many countries?
7. What's the trial status distribution?
8. How many FDA-regulated?
9. What's the average duration?
10. Are there Phase 4 trials?

---

## Running the Dashboard

### Local Development

```bash
cd "Projet3 dash V2"
pip install -r requirements.txt
python app.py
```

Open http://localhost:8050 in your browser.

### Production Deployment

Deploy to your preferred platform (Heroku, Vercel, GCP App Engine, etc.)

```bash
# Example: GCP App Engine
gcloud app deploy
```

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
1. Open https://1258ba9ffc834d3e8021b3b645bc5124-dot-us-central1.composer.googleusercontent.com
2. Click "DAGs" tab
3. Find "clinical_trials_etl_pipeline"
4. Check execution history and logs

### View Logs
```bash
gcloud composer environments run tracking-hope-airflow \
  --location us-central1 dags list
```

### Check Supabase Data
1. Go to https://supabase.com/dashboard
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
- Increase `execution_timeout` in DAG (currently 3 hours)
- Check ClinicalTrials.gov API status
- Monitor network connectivity

**Dashboard Not Showing Data:**
- Verify SUPABASE_URL and SUPABASE_KEY environment variables
- Check Supabase table has data
- Try clearing browser cache and reloading

---

## Performance

- **Extraction Time:** ~60 minutes per run
- **Records Processed:** 20,462 advanced trials per day
- **API Rate Limit:** 0.2-0.5 second delay between requests
- **Batch Size:** 200 records per database insert
- **Dashboard Load Time:** <2 seconds
- **Cost:** ~$0-10/month (GCP Composer + Supabase)

---

## Useful Links

- **Airflow UI:** https://1258ba9ffc834d3e8021b3b645bc5124-dot-us-central1.composer.googleusercontent.com
- **GCP Console:** https://console.cloud.google.com/composer/environments?project=clinical-trials-etl
- **GitHub Actions:** https://github.com/Ziad2727/clinical-trials-etl/actions
- **Supabase Dashboard:** https://supabase.com/dashboard

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

## Roadmap

### Short Term (Current Sprint)
- ETL Pipeline with Airflow
- Dash Dashboard with analytics
- Chatbot with FAQ
- Multi-language support
- [ ] Email alerts for new trials
- [ ] PDF export of Top 5

### Medium Term
- [ ] Advanced filtering (phase, sponsor, country)
- [ ] Trial comparison tool
- [ ] Mobile-responsive improvements
- [ ] User authentication & saved searches

### Long Term
- [ ] ML predictions (trial success rate by phase)
- [ ] Marketplace (researchers ↔ trials)
- [ ] Public API
- [ ] Researcher matching algorithm

---

**Last Updated:** April 23, 2026  
**Airflow Version:** 2.10.5  
**Composer Version:** 3  
**Dash Version:** 2.x  
**Status:** Production Ready ✅