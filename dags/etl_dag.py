"""
Airflow DAG for Clinical Trials ETL Pipeline
Complete version with all ETL code embedded
Uses HTTP requests to Supabase instead of supabase library
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
import pandas as pd
import time
import os
import json

# ============================================================================
# API CONFIGURATION
# ============================================================================

API_URL = "https://clinicaltrials.gov/api/v2/studies"
STATUS_FILTER = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,COMPLETED"
PAGE_SIZE = 1000
RATE_LIMIT_DELAY = 0.5

# ============================================================================
# DISEASE DEFINITIONS
# ============================================================================

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

# ============================================================================
# LOGGING UTILITY
# ============================================================================

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

# ============================================================================
# MAIN DATA EXTRACTION FUNCTION
# ============================================================================

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
                design_info = design_mod.get('designInfo', {})
                desc_mod = protocol.get('descriptionModule', {})
                sponsor_mod = protocol.get('sponsorCollaboratorsModule', {})
                lead_sponsor = sponsor_mod.get('leadSponsor', {})
                locations_mod = protocol.get('contactsLocationsModule', {})
                interv_mod = protocol.get('armsInterventionsModule', {})
                cond_mod = protocol.get('conditionsModule', {})
                oversight = protocol.get('oversightModule', {})

                phases = design_mod.get('phases', [])
                phase = ", ".join(phases) if phases else 'N/A'
                primary_purpose = design_info.get('primaryPurpose', 'N/A')
                enrollment = design_mod.get('enrollmentInfo', {}).get('count', 0) or 0
                has_results = study.get('hasResults', False)
                sponsor_type = lead_sponsor.get('class', 'N/A')
                is_fda = oversight.get('isFdaRegulatedDrug', False)

                locations = locations_mod.get('locations', [])
                countries = list(set(loc.get('country') for loc in locations if loc.get('country')))
                countries_str = ", ".join(countries)

                start_date = status_mod.get('startDateStruct', {}).get('date')
                end_date = (
                    status_mod.get('primaryCompletionDateStruct', {}).get('date') 
                    or status_mod.get('completionDateStruct', {}).get('date')
                )

                conditions_list = cond_mod.get('conditions', [])
                conditions_str = ", ".join(conditions_list)

                interventions = interv_mod.get('interventions', [])
                drug_names = list(dict.fromkeys([
                    i.get('name', '').strip() 
                    for i in interventions 
                    if i.get('type', '') in ('DRUG', 'BIOLOGICAL') 
                    and i.get('name', '').strip()
                ]))
                intervention_name = ', '.join(drug_names) if drug_names else 'N/A'

                brief_summary = desc_mod.get('briefSummary', 'N/A') if desc_mod else 'N/A'
                detailed_description = desc_mod.get('detailedDescription', 'N/A') if desc_mod else 'N/A'
                keywords_list = desc_mod.get('keywords', []) if desc_mod else []
                keywords_str = ", ".join(keywords_list) if keywords_list else 'N/A'

                results_section = study.get('resultsSection', {})
                primary_outcomes = results_section.get('primaryOutcomes', []) if results_section else []
                primary_outcome_str = (
                    ' | '.join([f"{o.get('measure', 'N/A')}" for o in primary_outcomes]) 
                    if primary_outcomes else 'N/A'
                )
                
                secondary_outcomes = results_section.get('secondaryOutcomes', []) if results_section else []
                secondary_outcome_str = (
                    ' | '.join([f"{o.get('measure', 'N/A')}" for o in secondary_outcomes]) 
                    if secondary_outcomes else 'N/A'
                )

                all_data.append({
                    'disease': disease_name,
                    'nctid': ident.get('nctId'),
                    'title': ident.get('briefTitle'),
                    'status': status_mod.get('overallStatus'),
                    'phase': phase,
                    'primarypurpose': primary_purpose,
                    'enrollment': enrollment,
                    'hasresults': has_results,
                    'sponsortype': sponsor_type,
                    'isfdaregulated': is_fda,
                    'locations': countries_str,
                    'conditions': conditions_str,
                    'interventionname': intervention_name,
                    'startdate': start_date,
                    'enddate': end_date,
                    'briefsummary': brief_summary,
                    'detaileddescription': detailed_description,
                    'keywords': keywords_str,
                    'primaryoutcomes': primary_outcome_str,
                    'secondaryoutcomes': secondary_outcome_str,
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
        df = df.fillna("Unknown")
        log_message(f"{disease_name} final: {len(df)}")
        return df

    return None

# ============================================================================
# MAIN ETL FUNCTION
# ============================================================================

def run_etl():
    log_message("="*80)
    log_message("Starting Clinical Trials ETL Pipeline")
    log_message("="*80)

    try:
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_KEY = os.getenv('SUPABASE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError(
                "Supabase credentials not found. "
                "Ensure SUPABASE_URL and SUPABASE_KEY are set in Cloud Composer environment."
            )
        
        log_message(f"Supabase URL: {SUPABASE_URL}")
        log_message("Supabase credentials loaded successfully")

        all_dfs = []

        for disease, query in DISEASES.items():
            df = extract_combined_data(disease, query)
            if df is not None:
                all_dfs.append(df)

        df_combined = pd.concat(all_dfs, ignore_index=True)
        df_combined = df_combined.drop_duplicates(subset=['nctid'])

        log_message(f"Total extracted: {len(df_combined)}")

        # Data cleaning
        df_combined["phase"] = df_combined["phase"].str.upper().str.strip()
        valid_phases = ['PHASE1', 'PHASE2', 'PHASE3', 'PHASE4']
        df_combined = df_combined[df_combined['phase'].isin(valid_phases)]

        log_message(f"After phase filter: {len(df_combined)}")

        # Clean text fields
        text_columns = [
            'briefsummary', 'detaileddescription', 'keywords',
            'primaryoutcomes', 'secondaryoutcomes'
        ]
        
        for col in text_columns:
            if col in df_combined.columns:
                df_combined[col] = df_combined[col].str.replace('\n', ' ', regex=False)
                df_combined[col] = df_combined[col].str.replace('\r', ' ', regex=False)
                df_combined[col] = df_combined[col].str.replace('  ', ' ', regex=False)

        df_combined = df_combined.replace('N/A', 'Unknown')

        log_message("Text fields cleaned")

        # ====================================================================
        # Load to Supabase using HTTP requests
        # ====================================================================
        
        headers = {
            'apikey': SUPABASE_KEY,
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }

        # First, truncate the table
        try:
            requests.delete(
                f"{SUPABASE_URL}/rest/v1/clinical_trials_combined?nctid=neq.null",
                headers=headers,
                timeout=15
            )
            log_message("Table truncated - ready for fresh load")
        except Exception as e:
            log_message(f"Warning: Could not truncate table: {e}")

        records = df_combined.to_dict(orient="records")
        BATCH_SIZE = 200

        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i+BATCH_SIZE]
            
            try:
                response = requests.post(
                    f"{SUPABASE_URL}/rest/v1/clinical_trials_combined",
                    headers=headers,
                    json=batch,
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    log_message(f"Batch {i//BATCH_SIZE + 1} inserted: {len(batch)} records")
                else:
                    log_message(f"Batch error: {response.status_code} - {response.text}")
            
            except Exception as e:
                log_message(f"Batch error: {e}")

        log_message(f"ETL COMPLETED: {len(records)} total records upserted")

    except Exception as e:
        log_message(f"ETL FAILED: {e}")
        raise

# ============================================================================
# DAG CONFIGURATION
# ============================================================================

default_args = {
    'owner': 'data-engineering',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': False,
    'email_on_retry': False,
    'start_date': datetime(2026, 4, 1),
    'execution_timeout': timedelta(seconds=1800),
}

dag = DAG(
    dag_id='clinical_trials_etl_pipeline',
    description='Extract, transform, and load clinical trials data from ClinicalTrials.gov to Supabase',
    default_args=default_args,
    schedule_interval='0 11 * * 1-5',
    max_active_runs=1,
    catchup=False,
    tags=['clinical-trials', 'etl', 'gcp', 'supabase'],
)

etl_task = PythonOperator(
    task_id='run_clinical_trials_etl',
    python_callable=run_etl,
    provide_context=True,
    dag=dag,
)

etl_task