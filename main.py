import requests 
import pandas as pd
from supabase import create_client
import time
from datetime import datetime
import os

# I normalize all keys to lowercase to match Supabase column names
def normalize_keys(d):
    return {k.lower(): v for k, v in d.items()}

# API configuration (ClinicalTrials.gov v2)
API_URL = "https://clinicaltrials.gov/api/v2/studies"
STATUS_FILTER = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,COMPLETED"
PAGE_SIZE = 1000
RATE_LIMIT_DELAY = 0.5

# Supabase configuration (credentials from environment variables)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://cmvnwgmcbmhpldluycya.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your_supabase_key")

# I define my list of diseases and associated search queries
DISEASES = {
    'Hypertension': 'Hypertension OR Arterial Hypertension OR Essential Hypertension OR High Blood Pressure',
    'Stroke': 'Stroke OR Ischemic Stroke OR Hemorrhagic Stroke OR Cerebrovascular Accident',
    'COPD': 'COPD OR Chronic Obstructive Pulmonary Disease OR Emphysema OR Chronic Bronchitis',
    'Tuberculosis': 'Tuberculosis OR TB OR Pulmonary Tuberculosis',
    'Malaria': 'Malaria',
    'Diabetes': 'Diabetes',
    'Major_Depressive_Disorder': 'Major Depressive Disorder',
    'Ehlers_Danlos_Syndrome': 'Ehlers-Danlos Syndrome',
    'Lung_Cancer': 'Lung Cancer OR NSCLC OR SCLC',
    'Ischemic_Heart_Disease': 'Ischemic Heart Disease OR Coronary Artery Disease OR Myocardial Infarction'
}

# I use a custom logger with timestamps for better debugging in GCP logs
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

# This function extracts and transforms data for a given disease
def extract_combined_data(disease_name, search_query):
    log_message(f"Extracting: {disease_name}")
    
    # I clean the disease name (important fix for matching conditions)
    clean_disease = disease_name.replace("_", " ").lower()
    
    params = {
        "query.cond": search_query,
        "filter.overallStatus": STATUS_FILTER,
        "pageSize": PAGE_SIZE
    }
    
    all_combined = []
    page_num = 1
    
    while True:
        try:
            response = None

            # I retry the API call up to 3 times in case of network issues
            for attempt in range(3):
                try:
                    response = requests.get(API_URL, params=params, timeout=15)
                    
                    if response.status_code == 200:
                        break
                    
                    log_message(f"Attempt {attempt+1} failed: {response.status_code}")
                    time.sleep(2)

                except requests.exceptions.RequestException as e:
                    log_message(f"Network error attempt {attempt+1}: {e}")
                    time.sleep(2)

            if response is None or response.status_code != 200:
                log_message("ERROR after retries")
                return None
            
            data = response.json()
            studies = data.get('studies', [])
            log_message(f"Page {page_num}: {len(studies)} studies")
            
            for study in studies:
                protocol = study.get('protocolSection', {})
                
                # I extract conditions and filter only relevant diseases
                cond_mod = protocol.get('conditionsModule', {})
                conditions_list = cond_mod.get('conditions', [])
                
                if not any(clean_disease in condition.lower() for condition in conditions_list):
                    continue
                
                # I keep only treatment/prevention studies
                design_mod = protocol.get('designModule', {})
                design_info = design_mod.get('designInfo', {})
                primary_purpose = design_info.get('primaryPurpose', 'N/A')
                
                if primary_purpose not in ['TREATMENT', 'PREVENTION']:
                    continue
                
                # I extract all relevant modules from the API response
                ident = protocol.get('identificationModule', {})
                status_mod = protocol.get('statusModule', {})
                sponsor_mod = protocol.get('sponsorCollaboratorsModule', {})
                lead_sponsor = sponsor_mod.get('leadSponsor', {})
                locations_mod = protocol.get('contactsLocationsModule', {})
                interv_mod = protocol.get('armsInterventionsModule', {})
                desc_mod = protocol.get('descriptionModule', {})
                
                # I format conditions and phases
                conditions_str = ", ".join(conditions_list)
                phases = design_mod.get('phases', [])
                phase = ", ".join(phases) if phases else 'N/A'
                
                # I extract key metadata
                enrollment = design_mod.get('enrollmentInfo', {}).get('count', 0) or 0
                sponsor_type = lead_sponsor.get('class', 'N/A')
                
                # I extract locations (countries only)
                locations = locations_mod.get('locations', [])
                countries = sorted(set(loc.get('country', 'N/A') for loc in locations if loc.get('country')))
                countries_str = ", ".join(countries)
                
                # I extract dates
                start_date = status_mod.get('startDateStruct', {}).get('date')
                end_date = status_mod.get('completionDateStruct', {}).get('date')
                
                # I extract drug interventions
                interventions = interv_mod.get('interventions', [])
                drug_names = list(dict.fromkeys([
                    i.get('name', '').strip()
                    for i in interventions
                    if i.get('type') in ('DRUG', 'BIOLOGICAL')
                ]))
                
                intervention_name = ', '.join(drug_names) if drug_names else 'N/A'
                
                # I extract descriptions and keywords
                brief_summary = desc_mod.get('briefSummary', 'N/A')
                detailed_description = desc_mod.get('detailedDescription', 'N/A')
                keywords = ", ".join(desc_mod.get('keywords', [])) if desc_mod.get('keywords') else 'N/A'
                
                # I append the cleaned record
                all_combined.append({
                    'Disease': disease_name,
                    'NCTId': ident.get('nctId'),
                    'Title': ident.get('briefTitle'),
                    'Status': status_mod.get('overallStatus', 'N/A'),
                    'Phase': phase,
                    'PrimaryPurpose': primary_purpose,
                    'Enrollment': enrollment,
                    'SponsorType': sponsor_type,
                    'Locations': countries_str,
                    'Conditions': conditions_str,
                    'InterventionName': intervention_name,
                    'StartDate': start_date,
                    'EndDate': end_date,
                    'BriefSummary': brief_summary,
                    'DetailedDescription': detailed_description,
                    'Keywords': keywords,
                })
            
            # I handle pagination using nextPageToken
            next_token = data.get('nextPageToken')
            if next_token:
                params['pageToken'] = next_token
                page_num += 1
                time.sleep(RATE_LIMIT_DELAY)
            else:
                break
        
        except requests.exceptions.RequestException as e:
            log_message(f"Network error: {e}")
            return None
    
    # I convert to DataFrame and remove duplicates
    if all_combined:
        df = pd.DataFrame(all_combined)
        df = df.drop_duplicates(subset=['NCTId'])
        df = df.fillna("Unknown")
        df = df.replace("", "Unknown")
        
        log_message(f"Final records: {len(df)}")
        return df
    else:
        log_message("No data found")
        return None

# Main ETL function (triggered by GCP)
def etl_combined(event, context):
    log_message("ETL STARTED")
    
    try:
        all_dataframes = []
        
        # I loop through all diseases
        for disease_name, search_query in DISEASES.items():
            df = extract_combined_data(disease_name, search_query)
            if df is not None:
                all_dataframes.append(df)
            else:
                log_message(f"FAILED: {disease_name}")
        
        if not all_dataframes:
            log_message("No data extracted")
            return
        
        # I merge all datasets
        df_combined = pd.concat(all_dataframes, ignore_index=True)
        df_combined = df_combined.drop_duplicates(subset=['NCTId'])
        
        log_message(f"Total records: {len(df_combined)}")
        
        # I initialize Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        BATCH_SIZE = 200
        
        # I convert DataFrame to list of dicts and normalize keys
        records = [normalize_keys(row) for row in df_combined.to_dict(orient="records")]
        
        # I insert data in batches
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i+BATCH_SIZE]
            
            try:
                supabase.table('clinical_trials_combined')\
                    .upsert(batch, on_conflict='nctid')\
                    .execute()
                
                log_message(f"Batch {i//BATCH_SIZE + 1} inserted")
            
            except Exception as e:
                log_message(f"Batch error: {e}")
        
        log_message("ETL COMPLETED")
    
    except Exception as e:
        log_message(f"ETL FAILED: {e}")