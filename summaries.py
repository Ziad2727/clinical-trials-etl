import requests
import pandas as pd
from supabase import create_client
import time
from datetime import datetime
import os

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://cmvnwgmcbmhpdluycya.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "ta_clé_anon")

API_URL = "https://clinicaltrials.gov/api/v2/studies"
STATUS_FILTER = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,COMPLETED"
PAGE_SIZE = 1000
RATE_LIMIT_DELAY = 0.5

DISEASES = {
    'Hypertension': 'Hypertension OR Arterial Hypertension OR Essential Hypertension OR High Blood Pressure OR Hypertension (HTN) OR Uncontrolled Hypertension OR Resistant Hypertension OR Resistant Arterial Hypertension OR Apparent Resistant Hypertension OR Nocturnal Hypertension OR stage1 Hypertension OR Uncontrolled Stage 2 Hypertension OR Subjects With Mild Hypertension OR Hypertension Arterial',
    'Stroke': 'Stroke OR Acute Stroke OR Chronic Stroke OR Ischemic Stroke OR Acute Ischemic Stroke OR Hemorrhagic Stroke OR Intracerebral Hemorrhage OR Cerebral Infarction OR Cerebrovascular Accident OR CVA (Cerebrovascular Accident) OR Lacunar Stroke OR Silent Stroke OR Pediatric Stroke OR Paediatric Stroke OR Perinatal Stroke OR Stroke Ischemic OR Ischaemic Stroke OR Isquemic Stroke OR Subacute Stroke OR Severe Stroke OR Mild Stroke OR Post Stroke OR High Risk of Stroke OR Stroke Acute OR Stroke Hemorrhagic OR Cerebrovascular Stroke OR Cerebral (CVAs) OR Stroke (CVA) or TIA OR Stroke (CVA) or Transient Ischemic Attack OR Chronic Ischemic Stroke OR Chronic Stroke Survivors OR Chronic Stroke Patients OR Right Hemisphere Stroke OR Brain Infarction OR Intracerebral Hemorrhagic Stroke OR Acute Mild Ischemic Stroke OR Stroke Sequelae OR Post-stroke',
    'COPD': 'COPD OR Chronic Obstructive Pulmonary Disease OR Emphysema OR Chronic Bronchitis OR Pulmonary Obstruction OR Airflow Obstruction OR Obstructive Lung Disease OR Chronic Airflow Obstruction OR Pulmonary Emphysema OR COPD Exacerbation OR Severe COPD OR Moderate COPD OR Mild COPD',
    'Tuberculosis': 'Tuberculosis OR Tuberculosis (TB) OR TUBERCULOSIS OR Pulmonary Tuberculosis OR Pulmonary Tuberculoses OR Pulmonary Tuberculosis (TB) OR Pulmonary TB OR Latent Tuberculosis OR Latent Tuberculosis Infection OR Tuberculosis Infection OR Tuberculosis Disease OR Tuberculosis Active OR Tuberculosis in Children OR Extrapulmonary Tuberculosis OR Disseminated Tuberculosis OR Multidrug-resistant Tuberculosis OR Multidrug Resistant Tuberculosis OR Multi Drug Resistant Tuberculosis OR Multidrug- and Rifampicin-resistant Tuberculosis OR Drug Resistant Tuberculosis OR Drug-resistant Tuberculosis OR Rifampin-resistant Tuberculosis OR Rifampin-Resistant Pulmonary Tuberculosis OR MDR-TB OR TB OR TB - Tuberculosis OR Reducing Tuberculosis Incidence',
    'Malaria': 'Malaria',
    'Diabetes': 'Diabetes',
    'Major_Depressive_Disorder': 'Major Depressive Disorder',
    'Ehlers_Danlos_Syndrome': 'Ehlers-Danlos Syndrome',
    'Lung_Cancer': 'Lung Cancer OR Trachea Cancer OR Bronchus Cancer OR Pulmonary Carcinoma OR Non-Small Cell Lung Cancer OR NSCLC OR Small Cell Lung Cancer OR SCLC OR Lung Adenocarcinoma OR Lung Tumor OR Bronchial Carcinoma',
    'Ischemic_Heart_Disease': 'Ischemic Heart Disease OR Coronary Artery Disease OR Myocardial Infarction OR Angina OR Coronary Ischemia OR Acute Coronary Syndrome OR Heart Attack OR CAD'
}

def log_message(message):
    """Log message to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)

def extract_study_summaries(disease_name, search_query):
    """Extract summaries for one disease"""
    log_message(f"Extracting summaries: {disease_name}")
    
    params = {
        "query.cond": search_query,
        "filter.overallStatus": STATUS_FILTER,
        "pageSize": PAGE_SIZE
    }
    
    all_summaries = []
    page_num = 1
    
    while True:
        log_message(f"  Page {page_num}...", end=" ")
        
        try:
            response = requests.get(API_URL, params=params, timeout=15)
            
            if response.status_code != 200:
                log_message(f"ERROR {response.status_code}")
                return None
            
            data = response.json()
            studies = data.get('studies', [])
            log_message(f"Found {len(studies)}")
            
            for study in studies:
                protocol = study.get('protocolSection', {})
                cond_mod = protocol.get('conditionsModule', {})
                conditions_list = cond_mod.get('conditions', [])
                
                keywords = [kw.strip().lower() for kw in search_query.split('OR')]
                
                found_match = False
                for condition in conditions_list:
                    condition_lower = condition.lower()
                    for keyword in keywords:
                        if keyword in condition_lower:
                            found_match = True
                            break
                    if found_match:
                        break
                
                if found_match:
                    design_mod = protocol.get('designModule', {})
                    design_info = design_mod.get('designInfo', {})
                    primary_purpose = design_info.get('primaryPurpose', 'N/A')
                    
                    if primary_purpose not in ['TREATMENT', 'PREVENTION']:
                        continue
                    
                    ident = protocol.get('identificationModule', {})
                    desc_mod = protocol.get('descriptionModule', {})
                    
                    phases = design_mod.get('phases', [])
                    phase = ", ".join(phases) if phases else 'N/A'
                    
                    brief_summary = desc_mod.get('briefSummary', 'N/A') if desc_mod else 'N/A'
                    detailed_description = desc_mod.get('detailedDescription', 'N/A') if desc_mod else 'N/A'
                    keywords_list = desc_mod.get('keywords', []) if desc_mod else []
                    keywords_str = ", ".join(keywords_list) if keywords_list else 'N/A'
                    
                    results_section = study.get('resultsSection', {})
                    
                    # Extract primary outcomes
                    primary_outcomes = results_section.get('primaryOutcomes', []) if results_section else []
                    primary_outcome_str = ''
                    if primary_outcomes:
                        for outcome in primary_outcomes:
                            measure = outcome.get('measure', 'N/A')
                            description = outcome.get('description', 'N/A')
                            time_frame = outcome.get('timeFrame', 'N/A')
                            primary_outcome_str += f"{measure} | {description} | TimeFrame: {time_frame}; "
                        primary_outcome_str = primary_outcome_str.strip()
                    else:
                        primary_outcome_str = 'N/A'
                    
                    # Extract secondary outcomes
                    secondary_outcomes = results_section.get('secondaryOutcomes', []) if results_section else []
                    secondary_outcome_str = ''
                    if secondary_outcomes:
                        for outcome in secondary_outcomes:
                            measure = outcome.get('measure', 'N/A')
                            description = outcome.get('description', 'N/A')
                            time_frame = outcome.get('timeFrame', 'N/A')
                            secondary_outcome_str += f"{measure} | {description} | TimeFrame: {time_frame}; "
                        secondary_outcome_str = secondary_outcome_str.strip()
                    else:
                        secondary_outcome_str = 'N/A'
                    
                    all_summaries.append({
                        'Disease': disease_name,
                        'NCTId': ident.get('nctId'),
                        'Phase': phase,
                        'BriefSummary': brief_summary,
                        'DetailedDescription': detailed_description,
                        'Keywords': keywords_str,
                        'PrimaryOutcomes': primary_outcome_str,
                        'SecondaryOutcomes': secondary_outcome_str,
                        'HasResults': bool(results_section)
                    })
            
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
    
    if all_summaries:
        df = pd.DataFrame(all_summaries)
        initial_count = len(df)
        
        df = df.drop_duplicates(subset=['NCTId'])
        df = df.fillna("Unknown")
        df = df.replace("", "Unknown")
        
        final_count = len(df)
        duplicates_removed = initial_count - final_count
        
        log_message(f"  Total: {initial_count} | Duplicates: {duplicates_removed} | Final: {final_count}")
        return df
    else:
        log_message(f"  No summaries found")
        return None

def etl_summaries(request):
    """Main ETL function for summaries"""
    log_message("="*80)
    log_message("ETL SUMMARIES STARTED")
    log_message("="*80)
    
    try:
        all_dataframes = []
        
        for disease_name, search_query in DISEASES.items():
            df = extract_study_summaries(disease_name, search_query)
            if df is not None:
                all_dataframes.append(df)
            else:
                log_message(f"FAILED to extract {disease_name}")
        
        if not all_dataframes:
            log_message("No summaries extracted")
            return {"status": "error", "message": "No summaries extracted"}, 500
        
        df_combined = pd.concat(all_dataframes, ignore_index=True)
        log_message(f"Total summaries extracted: {len(df_combined)}")
        log_message(f"Diseases extracted: {df_combined['Disease'].nunique()}")
        
        # Clean phases
        df_combined["Phase_clean"] = (
            df_combined["Phase"]
            .str.upper()
            .str.strip()
        )
        
        mapping = {
            "EARLY_PHASE1": "Early Phase 1",
            "PHASE1": "Phase 1",
            "PHASE2": "Phase 2",
            "PHASE3": "Phase 3",
            "PHASE4": "Phase 4",
            "PHASE1, PHASE2": "Phase 2",
            "PHASE2, PHASE3": "Phase 3",
            "PHASE3, PHASE4": "Phase 4",
            "PHASE NA": "Unknown",
            "N/A": "Unknown"
        }
        
        df_combined["Phase_clean"] = df_combined["Phase_clean"].replace(mapping)
        df_combined["Phase"] = df_combined["Phase_clean"]
        df_combined = df_combined.drop("Phase_clean", axis=1)
        
        log_message("Phase distribution after cleaning:")
        phase_counts = df_combined["Phase"].value_counts().to_dict()
        for phase, count in phase_counts.items():
            log_message(f"  {phase}: {count}")
        
        # Filter Phase 1, 2, 3, 4 only
        valid_phases = ['Early Phase 1', 'Phase 1', 'Phase 2', 'Phase 3', 'Phase 4']
        df_combined = df_combined[df_combined['Phase'].isin(valid_phases)]
        
        log_message(f"After filtering phases: {len(df_combined)} summaries")
        
        # Clean text fields - remove newlines
        text_columns = ['BriefSummary', 'DetailedDescription', 'Keywords', 
                        'PrimaryOutcomes', 'SecondaryOutcomes']
        
        for col in text_columns:
            if col in df_combined.columns:
                df_combined[col] = df_combined[col].str.replace('\n', ' ', regex=False)
                df_combined[col] = df_combined[col].str.replace('\r', ' ', regex=False)
                df_combined[col] = df_combined[col].str.replace('  ', ' ', regex=False)
        
        log_message("Text fields cleaned")
        
        # UPSERT to Supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        success = 0
        for idx, row in df_combined.iterrows():
            try:
                supabase.table('clinical_trials_summary').upsert(row.to_dict()).execute()
                success += 1
            except Exception as e:
                log_message(f"Error upserting {row['NCTId']}: {e}")
        
        log_message(f"Successfully upserted: {success} summaries")
        log_message("="*80)
        log_message("ETL SUMMARIES COMPLETED ✅")
        log_message("="*80)
        
        return {"status": "success", "summaries_loaded": success}, 200
    
    except Exception as e:
        log_message(f"ETL SUMMARIES FAILED: {e}")
        return {"status": "error", "message": str(e)}, 500