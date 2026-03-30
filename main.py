import base64
import requests
import time
from datetime import datetime
import os
from supabase import create_client

# ⚠️ PAS d'import pandas ici

API_URL = "https://clinicaltrials.gov/api/v2/studies"
STATUS_FILTER = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,COMPLETED"
PAGE_SIZE = 1000
RATE_LIMIT_DELAY = 0.5

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

DISEASES = {
    'Hypertension': 'Hypertension OR High Blood Pressure',
    'Stroke': 'Stroke OR Ischemic Stroke',
    'COPD': 'COPD OR Chronic Obstructive Pulmonary Disease',
    'Tuberculosis': 'Tuberculosis OR TB',
    'Malaria': 'Malaria',
    'Diabetes': 'Diabetes',
    'Major_Depressive_Disorder': 'Major Depressive Disorder',
    'Ehlers_Danlos_Syndrome': 'Ehlers-Danlos Syndrome',
    'Lung_Cancer': 'Lung Cancer',
    'Ischemic_Heart_Disease': 'Ischemic Heart Disease'
}

def log_message(message):
    print(f"[{datetime.now()}] {message}")

def extract_disease_trials(disease_name, search_query):
    log_message(f"Extracting: {disease_name}")

    params = {
        "query.cond": search_query,
        "filter.overallStatus": STATUS_FILTER,
        "pageSize": PAGE_SIZE
    }

    all_trials = []

    while True:
        try:
            response = requests.get(API_URL, params=params, timeout=15)

            if response.status_code != 200:
                log_message(f"ERROR {response.status_code}")
                return []

            data = response.json()
            studies = data.get('studies', [])

            for study in studies:
                protocol = study.get('protocolSection', {})
                ident = protocol.get('identificationModule', {})
                status_mod = protocol.get('statusModule', {})
                design_mod = protocol.get('designModule', {})

                trial = {
                    'Disease': disease_name,
                    'NCTId': ident.get('nctId'),
                    'Title': ident.get('briefTitle'),
                    'Status': status_mod.get('overallStatus'),
                    'Phase': ", ".join(design_mod.get('phases', [])) or "Unknown"
                }

                if trial['NCTId']:
                    all_trials.append(trial)

            next_token = data.get('nextPageToken')
            if not next_token:
                break

            params['pageToken'] = next_token
            time.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            log_message(f"ERROR: {e}")
            return []

    return all_trials

def etl_trials(event, context):
    log_message("ETL START")

    try:
        # 🔥 Import pandas ici uniquement
        import pandas as pd

        all_data = []

        for disease, query in DISEASES.items():
            data = extract_disease_trials(disease, query)
            all_data.extend(data)

        if not all_data:
            log_message("No data")
            return

        df = pd.DataFrame(all_data)

        log_message(f"Rows: {len(df)}")

        # nettoyage simple
        df = df.drop_duplicates(subset=["NCTId"])
        df = df.fillna("Unknown")

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # ⚡ batch insert (beaucoup plus rapide)
        data_to_insert = df.to_dict(orient="records")

        supabase.table("clinical_trials").upsert(data_to_insert).execute()

        log_message("UPLOAD OK")

    except Exception as e:
        log_message(f"FAIL: {e}")
        raise

print("CLEAN BUILD FINAL")