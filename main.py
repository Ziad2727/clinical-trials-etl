import base64
import requests
import pandas as pd
from supabase import create_client
import time
from datetime import datetime
import os

# Set the API endpoint for ClinicalTrials.gov
API_URL = "https://clinicaltrials.gov/api/v2/studies"

# Filter for study status - only include recruiting and completed studies
STATUS_FILTER = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,COMPLETED"

# Number of results per API page request
PAGE_SIZE = 1000

# Delay between API requests to avoid rate limiting
RATE_LIMIT_DELAY = 0.5

# Get Supabase connection details from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://cmvnwgmcbmhpldluycya.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "ta_clé_anon")

# Dictionary containing the 10 diseases and their search queries
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
    # Create a timestamp for the log entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Format the log message with timestamp
    log_line = f"[{timestamp}] {message}"
    # Print the log message to console
    print(log_line)

def extract_disease_trials(disease_name, search_query):
    # Print the name of the disease being extracted
    log_message(f"Extracting: {disease_name}")
    
    # Set up the API request parameters
    params = {
        "query.cond": search_query,
        "filter.overallStatus": STATUS_FILTER,
        "pageSize": PAGE_SIZE
    }
    
    # Initialize list to store all trial data
    all_trials = []
    # Track the current page number for pagination
    page_num = 1
    
    # Loop through all pages of results
    while True:
        try:
            # Make HTTP GET request to the API
            response = requests.get(API_URL, params=params, timeout=15)
            
            # Check if the response status is OK
            if response.status_code != 200:
                log_message(f"  ERROR {response.status_code}")
                return None
            
            # Parse the JSON response
            data = response.json()
            # Extract the list of studies from the response
            studies = data.get('studies', [])
            # Log the number of studies found on this page
            log_message(f"  Page {page_num}: {len(studies)} studies")
            
            # Process each study in the current page
            for study in studies:
                # Extract the protocol section of the study
                protocol = study.get('protocolSection', {})
                # Extract the conditions module
                cond_mod = protocol.get('conditionsModule', {})
                # Get the list of conditions for this trial
                conditions_list = cond_mod.get('conditions', [])
                
                # Convert the search query into individual keywords
                keywords = [kw.strip().lower() for kw in search_query.split('OR')]
                
                # Check if any of the keywords match the trial conditions
                found_match = False
                for condition in conditions_list:
                    condition_lower = condition.lower()
                    for keyword in keywords:
                        if keyword in condition_lower:
                            found_match = True
                            break
                    if found_match:
                        break
                
                # Only process this trial if it matches the disease query
                if found_match:
                    # Extract the design module
                    design_mod = protocol.get('designModule', {})
                    # Extract design information
                    design_info = design_mod.get('designInfo', {})
                    # Get the primary purpose of the trial
                    primary_purpose = design_info.get('primaryPurpose', 'N/A')
                    
                    # Only include trials with TREATMENT or PREVENTION purpose
                    if primary_purpose not in ['TREATMENT', 'PREVENTION']:
                        continue
                    
                    # Extract the identification module
                    ident = protocol.get('identificationModule', {})
                    # Extract the status module
                    status_mod = protocol.get('statusModule', {})
                    # Extract oversight information
                    oversight = protocol.get('oversightModule', {})
                    # Extract sponsor information
                    sponsor_mod = protocol.get('sponsorCollaboratorsModule', {})
                    # Get the lead sponsor details
                    lead_sponsor = sponsor_mod.get('leadSponsor', {})
                    # Extract location information
                    locations_mod = protocol.get('contactsLocationsModule', {})
                    # Extract intervention information
                    interv_mod = protocol.get('armsInterventionsModule', {})
                    
                    # Join all conditions into a single string
                    conditions_str = ", ".join(conditions_list)
                    # Get the list of trial phases
                    phases = design_mod.get('phases', [])
                    # Join phases into a single string
                    phase = ", ".join(phases) if phases else 'N/A'
                    # Extract enrollment information
                    enrollment_info = design_mod.get('enrollmentInfo', {})
                    # Get the enrollment count
                    enrollment = enrollment_info.get('count', 0) or 0
                    # Check if the trial has results available
                    has_results = study.get('hasResults', False)
                    # Get the sponsor type
                    sponsor_type = lead_sponsor.get('class', 'N/A')
                    # Check if the drug is FDA regulated
                    is_fda = oversight.get('isFdaRegulatedDrug', False)
                    
                    # Extract locations from the study
                    locations = locations_mod.get('locations', [])
                    # Get unique countries from the locations
                    countries = sorted(set(
                        loc.get('country', 'N/A') for loc in locations if loc.get('country')
                    ))
                    # Join countries into a single string
                    countries_str = ", ".join(countries)
                    
                    # Get the study start date
                    start_date = status_mod.get('startDateStruct', {}).get('date')
                    # Get the study end date (primary completion or completion date)
                    end_date = (status_mod.get('primaryCompletionDateStruct', {}).get('date')
                               or status_mod.get('completionDateStruct', {}).get('date'))
                    
                    # Extract intervention information
                    interventions = interv_mod.get('interventions', [])
                    # Get drug names from interventions
                    drug_names = list(dict.fromkeys([
                        i.get('name', '').strip()
                        for i in interventions
                        if i.get('type', '') in ('DRUG', 'BIOLOGICAL') and i.get('name', '').strip()
                    ]))
                    # Join drug names into a single string
                    intervention_name = ', '.join(drug_names) if drug_names else 'N/A'
                    
                    # Create a dictionary with all trial information
                    all_trials.append({
                        'Disease': disease_name,
                        'NCTId': ident.get('nctId'),
                        'Title': ident.get('briefTitle'),
                        'Status': status_mod.get('overallStatus', 'N/A'),
                        'Phase': phase,
                        'PrimaryPurpose': primary_purpose,
                        'Enrollment': enrollment,
                        'HasResults': has_results,
                        'SponsorType': sponsor_type,
                        'IsFdaRegulated': is_fda,
                        'Locations': countries_str,
                        'Conditions': conditions_str,
                        'InterventionName': intervention_name,
                        'StartDate': start_date,
                        'EndDate': end_date,
                    })
            
            # Check if there are more pages of results
            next_token = data.get('nextPageToken')
            if next_token:
                # Add the next page token to the parameters
                params['pageToken'] = next_token
                # Increment the page number
                page_num += 1
                # Wait before making the next request to avoid rate limiting
                time.sleep(RATE_LIMIT_DELAY)
            else:
                # Exit the loop if there are no more pages
                break
        
        except requests.exceptions.RequestException as e:
            # Log any network errors
            log_message(f"Network error: {e}")
            return None
    
    # Check if any trials were found
    if all_trials:
        # Create a DataFrame from the trials list
        df = pd.DataFrame(all_trials)
        # Count the initial number of trials
        initial_count = len(df)
        
        # Remove duplicate trials based on NCTId
        df = df.drop_duplicates(subset=['NCTId'])
        # Fill missing values with "Unknown"
        df = df.fillna("Unknown")
        # Replace empty strings with "Unknown"
        df = df.replace("", "Unknown")
        
        # Count the final number of trials
        final_count = len(df)
        # Calculate the number of duplicates removed
        duplicates_removed = initial_count - final_count
        
        # Log the extraction results
        log_message(f"  Total: {initial_count} | Duplicates: {duplicates_removed} | Final: {final_count}")
        return df
    else:
        # Log if no trials were found
        log_message(f"  No trials found")
        return None

def etl_trials(event, context):
    # Log the start of the ETL process
    log_message("="*80)
    log_message("ETL TRIALS STARTED")
    log_message("="*80)
    
    try:
        # Initialize list to store DataFrames for each disease
        all_dataframes = []
        
        # Process each disease
        for disease_name, search_query in DISEASES.items():
            # Extract trials for this disease
            df = extract_disease_trials(disease_name, search_query)
            # Check if extraction was successful
            if df is not None:
                # Add the DataFrame to the list
                all_dataframes.append(df)
            else:
                # Log failed extractions
                log_message(f"FAILED to extract {disease_name}")
        
        # Check if any data was extracted
        if not all_dataframes:
            log_message("No data extracted")
            return
        
        # Combine all DataFrames into one
        df_combined = pd.concat(all_dataframes, ignore_index=True)
        # Log the total number of trials extracted
        log_message(f"Total trials extracted: {len(df_combined)}")
        # Log the number of unique diseases
        log_message(f"Diseases extracted: {df_combined['Disease'].nunique()}")
        
        # Create a new column for phase cleaning
        df_combined["Phase_clean"] = (
            df_combined["Phase"]
            .str.upper()
            .str.strip()
        )
        
        # Map phase names to standard format
        mapping = {
            "EARLY_PHASE1": "Early Phase 1",
            "PHASE1": "Phase 1",
            "PHASE2": "Phase 2",
            "PHASE3": "Phase 3",
            "PHASE4": "Phase 4",
            "PHASE1, PHASE2": "Phase 2",
            "PHASE2, PHASE3": "Phase 3",
            "PHASE3, PHASE4": "Phase 4",
            "N/A": "Unknown"
        }
        
        # Replace phase values using the mapping
        df_combined["Phase_clean"] = df_combined["Phase_clean"].replace(mapping)
        # Replace the original Phase column with cleaned values
        df_combined["Phase"] = df_combined["Phase_clean"]
        # Drop the temporary Phase_clean column
        df_combined = df_combined.drop("Phase_clean", axis=1)
        
        # Log the phase distribution
        log_message("Phase distribution after cleaning:")
        # Get the count of each phase
        phase_counts = df_combined["Phase"].value_counts().to_dict()
        # Log each phase count
        for phase, count in phase_counts.items():
            log_message(f"  {phase}: {count}")
        
        # Define valid phase values
        valid_phases = ['Early Phase 1', 'Phase 1', 'Phase 2', 'Phase 3', 'Phase 4']
        # Filter to keep only valid phases
        df_combined = df_combined[df_combined['Phase'].isin(valid_phases)]
        
        # Log the number of trials after filtering
        log_message(f"After filtering phases: {len(df_combined)} trials")
        
        # Create a Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Initialize counter for successful uploads
        success = 0
        # Iterate through each row and upload to Supabase
        for idx, row in df_combined.iterrows():
            try:
                # Upsert the row into the clinical_trials table
                supabase.table('clinical_trials').upsert(row.to_dict()).execute()
                # Increment the success counter
                success += 1
            except Exception as e:
                # Log any errors during upload
                log_message(f"Error upserting {row['NCTId']}: {e}")
        
        # Log the number of successfully uploaded trials
        log_message(f"Successfully upserted: {success} trials")
        # Log the completion of the ETL process
        log_message("="*80)
        log_message("ETL TRIALS COMPLETED")
        log_message("="*80)
    
    except Exception as e:
        # Log any errors in the main ETL process
        log_message(f"ETL TRIALS FAILED: {e}")