import requests
import pandas as pd
from supabase import create_client
import time
from datetime import datetime
import os


# API Configuration
API_URL = "https://clinicaltrials.gov/api/v2/studies"
STATUS_FILTER = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,COMPLETED"
PAGE_SIZE = 1000
RATE_LIMIT_DELAY = 0.5


# Supabase Configuration (use environment variables)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


# Disease queries
DISEASES = {
    'Hypertension': 'Hypertension OR Arterial Hypertension OR High Blood Pressure',
    'Stroke': 'Stroke OR Ischemic Stroke OR Hemorrhagic Stroke',
    'COPD': 'COPD OR Chronic Obstructive Pulmonary Disease',
    'Tuberculosis': 'Tuberculosis OR TB',
    'Malaria': 'Malaria',
    'Diabetes': 'Diabetes',
    'Major_Depressive_Disorder': 'Major Depressive Disorder',
    'Ehlers_Danlos_Syndrome': 'Ehlers-Danlos Syndrome',
    'Lung_Cancer': 'Lung Cancer OR NSCLC OR SCLC',
    'Ischemic_Heart_Disease': 'Ischemic Heart Disease OR Coronary Artery Disease'
}


def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def extract_combined_data(disease_name, search_query):
    log_message(f"Extracting: {disease_name}")

    params = {
        "query.cond": search_query,
        "filter.overallStatus": STATUS_FILTER,
        "pageSize": PAGE_SIZE
    }

    all_data = []
    page_num = 1

    while True:
        try:
            response = requests.get(API_URL, params=params, timeout=15)

            if response.status_code != 200:
                log_message(f"ERROR API {response.status_code}")
                return None

            data = response.json()
            studies = data.get('studies', [])

            log_message(f"Page {page_num}: {len(studies)} studies")

            for study in studies:
                protocol = study.get('protocolSection', {})

                ident = protocol.get('identificationModule', {})
                status_mod = protocol.get('statusModule', {})
                design_mod = protocol.get('designModule', {})
                desc_mod = protocol.get('descriptionModule', {})
                sponsor_mod = protocol.get('sponsorCollaboratorsModule', {})
                locations_mod = protocol.get('contactsLocationsModule', {})

                phases = design_mod.get('phases', [])
                phase = ", ".join(phases) if phases else 'N/A'

                locations = locations_mod.get('locations', [])
                countries = list(set(loc.get('country') for loc in locations if loc.get('country')))
                countries_str = ", ".join(countries)

                all_data.append({
                    'disease': disease_name,
                    'nctid': ident.get('nctId'),
                    'title': ident.get('briefTitle'),
                    'status': status_mod.get('overallStatus'),
                    'phase': phase,
                    'startdate': status_mod.get('startDateStruct', {}).get('date'),
                    'locations': countries_str,
                    'briefsummary': desc_mod.get('briefSummary', 'N/A'),
                })

            next_token = data.get('nextPageToken')

            if next_token:
                params['pageToken'] = next_token
                page_num += 1
                time.sleep(RATE_LIMIT_DELAY)
            else:
                break

        except Exception as e:
            log_message(f"ERROR: {e}")
            return None

    if all_data:
        df = pd.DataFrame(all_data)

        df = df.drop_duplicates(subset=['nctid'])

        log_message(f"{disease_name} final: {len(df)}")

        return df

    return None


def etl_combined(event, context):
    log_message("ETL STARTED")

    try:
        all_dfs = []

        for disease, query in DISEASES.items():
            df = extract_combined_data(disease, query)
            if df is not None:
                all_dfs.append(df)

        df_combined = pd.concat(all_dfs, ignore_index=True)

        df_combined = df_combined.drop_duplicates(subset=['nctid'])

        log_message(f"Total extracted: {len(df_combined)}")

        # Clean Phase
        df_combined["phase"] = df_combined["phase"].str.upper().str.strip()

        valid_phases = ['PHASE1', 'PHASE2', 'PHASE3', 'PHASE4']
        df_combined = df_combined[df_combined['phase'].isin(valid_phases)]

        log_message(f"After phase filter: {len(df_combined)}")

        # Supabase connection
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        records = df_combined.to_dict(orient="records")

        BATCH_SIZE = 200

        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i+BATCH_SIZE]

            try:
                supabase.table('clinical_trials_combined') \
                    .upsert(batch) \
                    .execute()

                log_message(f"Batch {i//BATCH_SIZE + 1} inserted: {len(batch)} records")

            except Exception as e:
                log_message(f"Batch error: {e}")

        log_message(f"ETL COMPLETED: {len(records)} total records upserted")

    except Exception as e:
        log_message(f"ETL FAILED: {e}")