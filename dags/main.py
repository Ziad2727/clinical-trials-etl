"""
Clinical Trials ETL Pipeline - Complete Version
================================================

This module implements a comprehensive Extract-Transform-Load (ETL) pipeline that:
1. Extracts clinical trial data from ClinicalTrials.gov API for 10 diseases
2. Extracts ALL available trial information including phases, enrollment, outcomes, etc.
3. Transforms and cleans the data (remove duplicates, standardize formats, etc.)
4. Loads the complete processed data into Supabase PostgreSQL database

The pipeline is designed to run automatically via Google Cloud Functions
and Cloud Scheduler, executing daily at 11:00 AM UTC (Monday-Friday).

This version extracts 20+ fields per trial to provide comprehensive data for analysis.

"""

import requests
import pandas as pd
from supabase import create_client
import time
from datetime import datetime
import os


# ============================================================================
# API CONFIGURATION
# ============================================================================

# Base URL for the ClinicalTrials.gov API v2 endpoint
# This API provides access to registered clinical trial information
API_URL = "https://clinicaltrials.gov/api/v2/studies"

# Filter to only include studies with these recruitment statuses
# These statuses represent active or recently completed trials
STATUS_FILTER = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,COMPLETED"

# Number of results to fetch per API request
# Maximum allowed by ClinicalTrials.gov API is 1000
PAGE_SIZE = 1000

# Delay between API requests to respect rate limits and avoid blocking
# Prevents overwhelming the API server
RATE_LIMIT_DELAY = 0.5


# ============================================================================
# SUPABASE CONFIGURATION
# ============================================================================

# Supabase database URL - retrieved from environment variables for security
# Never hardcode credentials in production code
SUPABASE_URL = os.getenv("SUPABASE_URL")

# Supabase anonymous API key - retrieved from environment variables
# Provides access to the PostgreSQL database through the REST API
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


# ============================================================================
# DISEASE DEFINITIONS
# ============================================================================

# Dictionary mapping disease names to their search queries for the API
# Each query uses OR operators to capture variations of disease terminology
# This ensures we capture all relevant clinical trials for each disease
DISEASES = {
    # Hypertension (high blood pressure) - includes common variations
    'Hypertension': 'Hypertension OR Arterial Hypertension OR High Blood Pressure',
    
    # Stroke - includes ischemic and hemorrhagic types
    'Stroke': 'Stroke OR Ischemic Stroke OR Hemorrhagic Stroke',
    
    # COPD - Chronic Obstructive Pulmonary Disease
    'COPD': 'COPD OR Chronic Obstructive Pulmonary Disease',
    
    # Tuberculosis - includes common abbreviation TB
    'Tuberculosis': 'Tuberculosis OR TB',
    
    # Malaria - parasitic infectious disease
    'Malaria': 'Malaria',
    
    # Diabetes - metabolic disorder affecting blood glucose
    'Diabetes': 'Diabetes',
    
    # Major Depressive Disorder - psychiatric condition
    'Major_Depressive_Disorder': 'Major Depressive Disorder',
    
    # Ehlers-Danlos Syndrome - genetic connective tissue disorder
    'Ehlers_Danlos_Syndrome': 'Ehlers-Danlos Syndrome',
    
    # Lung Cancer - includes common variants (NSCLC, SCLC)
    'Lung_Cancer': 'Lung Cancer OR NSCLC OR SCLC',
    
    # Ischemic Heart Disease - inadequate blood flow to the heart
    'Ischemic_Heart_Disease': 'Ischemic Heart Disease OR Coronary Artery Disease'
}


# ============================================================================
# LOGGING UTILITY
# ============================================================================

def log_message(message):
    """
    Print timestamped log messages for debugging and monitoring.
    
    This function formats log messages with a timestamp prefix, making it easy
    to track when events occur during pipeline execution. Logs are visible in
    Google Cloud Functions console.
    
    Args:
        message (str): The message to log
        
    Example:
        log_message("Extracting: Hypertension")
        # Output: [2026-04-02 11:00:00] Extracting: Hypertension
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


# ============================================================================
# MAIN DATA EXTRACTION FUNCTION
# ============================================================================

def extract_combined_data(disease_name, search_query):
    """
    Extract comprehensive clinical trial data from ClinicalTrials.gov API.
    
    This function:
    1. Sends paginated requests to the API using the disease search query
    2. Extracts ALL relevant trial information (20+ fields per trial)
    3. Handles pagination to retrieve all available results
    4. Removes duplicate studies based on NCTId
    5. Returns a pandas DataFrame with the complete cleaned data
    
    Fields extracted:
    - Basic info: disease, nctid, title, status
    - Trial design: phase, primarypurpose, enrollment
    - Locations: locations, conditions
    - Sponsorship: sponsortype, isfdaregulated
    - Treatments: interventionname
    - Dates: startdate, enddate
    - Summaries: briefsummary, detaileddescription, keywords
    - Outcomes: primaryoutcomes, secondaryoutcomes
    - Results: hasresults
    
    Args:
        disease_name (str): Name of the disease (e.g., 'Hypertension')
        search_query (str): API search query with disease keywords
        
    Returns:
        pd.DataFrame: DataFrame with complete trial data or None if extraction fails
        
    Raises:
        Catches requests exceptions and returns None on API errors
        
    Note:
        - API responses are paginated (max 1000 results per request)
        - Uses pageToken to retrieve subsequent pages
        - Implements rate limiting between requests
    """
    
    log_message(f"Extracting: {disease_name}")

    # Build the API request parameters
    # These parameters filter trials by condition and status
    params = {
        "query.cond": search_query,  # Search by condition/disease
        "filter.overallStatus": STATUS_FILTER,  # Filter by status
        "pageSize": PAGE_SIZE  # Number of results per page
    }

    # Initialize empty list to accumulate all trial records
    all_data = []
    page_num = 1  # Track which page we're currently fetching

    # Loop through all pages of API results
    while True:
        try:
            # Make HTTP GET request to ClinicalTrials.gov API
            # Timeout of 15 seconds prevents hanging on slow connections
            response = requests.get(API_URL, params=params, timeout=15)

            # Check if the API request was successful
            if response.status_code != 200:
                log_message(f"ERROR API {response.status_code}")
                return None

            # Parse the JSON response into a Python dictionary
            data = response.json()
            
            # Extract the list of studies from the response
            studies = data.get('studies', [])

            # Log progress: how many studies are on this page
            log_message(f"Page {page_num}: {len(studies)} studies")

            # Process each study returned from the API
            for study in studies:
                # Navigate the nested JSON structure to extract trial information
                # The protocolSection contains all relevant trial metadata
                protocol = study.get('protocolSection', {})

                # ============================================================
                # Extract different sections of the protocol
                # ============================================================
                
                # Identification Module - Basic trial identification info
                ident = protocol.get('identificationModule', {})
                
                # Status Module - Trial current status and important dates
                status_mod = protocol.get('statusModule', {})
                
                # Design Module - Trial design characteristics and phases
                design_mod = protocol.get('designModule', {})
                design_info = design_mod.get('designInfo', {})
                
                # Description Module - Summaries and detailed descriptions
                desc_mod = protocol.get('descriptionModule', {})
                
                # Sponsor Module - Information about trial sponsors
                sponsor_mod = protocol.get('sponsorCollaboratorsModule', {})
                lead_sponsor = sponsor_mod.get('leadSponsor', {})
                
                # Locations Module - Geographic locations where trial is conducted
                locations_mod = protocol.get('contactsLocationsModule', {})
                
                # Interventions Module - Drugs/treatments being tested
                interv_mod = protocol.get('armsInterventionsModule', {})
                
                # Conditions Module - Medical conditions being studied
                cond_mod = protocol.get('conditionsModule', {})
                
                # Oversight Module - FDA regulation info
                oversight = protocol.get('oversightModule', {})

                # ============================================================
                # Extract and transform BASIC INFORMATION
                # ============================================================
                
                # Trial phases indicate the development stage
                # Phases: Early Phase 1, Phase 1, 2, 3, 4
                phases = design_mod.get('phases', [])
                phase = ", ".join(phases) if phases else 'N/A'

                # Primary purpose of the trial (TREATMENT, PREVENTION, etc.)
                primary_purpose = design_info.get('primaryPurpose', 'N/A')

                # Number of participants enrolled in the trial
                enrollment = design_mod.get('enrollmentInfo', {}).get('count', 0) or 0

                # Whether trial has published results
                has_results = study.get('hasResults', False)

                # Sponsor type (INDUSTRY, ACADEMIC, etc.)
                sponsor_type = lead_sponsor.get('class', 'N/A')

                # Whether the drug/intervention is FDA regulated
                is_fda = oversight.get('isFdaRegulatedDrug', False)

                # ============================================================
                # Extract LOCATIONS (countries where trial is conducted)
                # ============================================================
                
                locations = locations_mod.get('locations', [])
                countries = list(set(
                    loc.get('country') for loc in locations if loc.get('country')
                ))
                countries_str = ", ".join(countries)

                # ============================================================
                # Extract DATES
                # ============================================================
                
                # When the trial started
                start_date = status_mod.get('startDateStruct', {}).get('date')
                
                # When the trial ended or is expected to end
                end_date = (
                    status_mod.get('primaryCompletionDateStruct', {}).get('date') 
                    or status_mod.get('completionDateStruct', {}).get('date')
                )

                # ============================================================
                # Extract CONDITIONS (medical conditions being studied)
                # ============================================================
                
                conditions_list = cond_mod.get('conditions', [])
                conditions_str = ", ".join(conditions_list)

                # ============================================================
                # Extract INTERVENTIONS (drugs/treatments being tested)
                # ============================================================
                
                interventions = interv_mod.get('interventions', [])
                # Extract drug names from interventions
                # Only include DRUG and BIOLOGICAL type interventions
                drug_names = list(dict.fromkeys([
                    i.get('name', '').strip() 
                    for i in interventions 
                    if i.get('type', '') in ('DRUG', 'BIOLOGICAL') 
                    and i.get('name', '').strip()
                ]))
                intervention_name = ', '.join(drug_names) if drug_names else 'N/A'

                # ============================================================
                # Extract DESCRIPTIONS AND SUMMARIES
                # ============================================================
                
                # Brief summary of the trial
                brief_summary = desc_mod.get('briefSummary', 'N/A') if desc_mod else 'N/A'
                
                # Detailed scientific description of the trial
                detailed_description = (
                    desc_mod.get('detailedDescription', 'N/A') if desc_mod else 'N/A'
                )
                
                # Keywords associated with the trial
                keywords_list = desc_mod.get('keywords', []) if desc_mod else []
                keywords_str = ", ".join(keywords_list) if keywords_list else 'N/A'

                # ============================================================
                # Extract OUTCOMES
                # ============================================================
                
                results_section = study.get('resultsSection', {})
                
                # Primary outcomes - main things being measured
                primary_outcomes = (
                    results_section.get('primaryOutcomes', []) 
                    if results_section else []
                )
                primary_outcome_str = (
                    ' | '.join([f"{o.get('measure', 'N/A')}" for o in primary_outcomes]) 
                    if primary_outcomes else 'N/A'
                )
                
                # Secondary outcomes - additional things being measured
                secondary_outcomes = (
                    results_section.get('secondaryOutcomes', []) 
                    if results_section else []
                )
                secondary_outcome_str = (
                    ' | '.join([f"{o.get('measure', 'N/A')}" for o in secondary_outcomes]) 
                    if secondary_outcomes else 'N/A'
                )

                # ============================================================
                # CREATE RECORD WITH ALL EXTRACTED DATA
                # ============================================================
                
                # All keys are lowercase to match Supabase column names
                all_data.append({
                    # Basic identification
                    'disease': disease_name,  # Which disease this trial is for
                    'nctid': ident.get('nctId'),  # National Clinical Trial ID (unique)
                    'title': ident.get('briefTitle'),  # Brief title of the trial
                    
                    # Status and design
                    'status': status_mod.get('overallStatus'),  # Current status
                    'phase': phase,  # Trial phase (I, II, III, IV)
                    'primarypurpose': primary_purpose,  # TREATMENT, PREVENTION, etc.
                    
                    # Enrollment and results
                    'enrollment': enrollment,  # Number of participants
                    'hasresults': has_results,  # Whether results are published
                    
                    # Sponsorship and regulation
                    'sponsortype': sponsor_type,  # INDUSTRY, ACADEMIC, etc.
                    'isfdaregulated': is_fda,  # FDA regulation status
                    
                    # Geographic and medical info
                    'locations': countries_str,  # Countries where trial runs
                    'conditions': conditions_str,  # Medical conditions studied
                    'interventionname': intervention_name,  # Drugs/treatments tested
                    
                    # Timeline
                    'startdate': start_date,  # When trial started
                    'enddate': end_date,  # When trial ended/will end
                    
                    # Descriptions
                    'briefsummary': brief_summary,  # Brief description
                    'detaileddescription': detailed_description,  # Detailed description
                    'keywords': keywords_str,  # Associated keywords
                    
                    # Outcomes
                    'primaryoutcomes': primary_outcome_str,  # Primary measurements
                    'secondaryoutcomes': secondary_outcome_str,  # Secondary measurements
                })

            # Check if there are more pages of results
            next_token = data.get('nextPageToken')

            # If nextPageToken exists, we have more results to fetch
            if next_token:
                params['pageToken'] = next_token  # Add token to params for next request
                page_num += 1  # Increment page counter
                time.sleep(RATE_LIMIT_DELAY)  # Wait before next API call (rate limiting)
            else:
                # No more pages - we've retrieved all results
                break

        except Exception as e:
            # Catch any unexpected errors (network issues, API changes, etc.)
            log_message(f"ERROR: {e}")
            return None

    # Convert the list of dictionaries into a pandas DataFrame
    if all_data:
        df = pd.DataFrame(all_data)

        # Remove duplicate trials that may have been returned in multiple pages
        # NCTId is unique identifier for each clinical trial
        df = df.drop_duplicates(subset=['nctid'])

        # Fill missing values with 'Unknown' for string columns
        # This prevents NULL values in the database
        df = df.fillna("Unknown")

        # Log final count for this disease
        log_message(f"{disease_name} final: {len(df)}")

        return df

    # If no data was extracted, return None
    return None


# ============================================================================
# MAIN ETL FUNCTION
# ============================================================================

def etl_combined(event, context):
    """
    Main ETL pipeline function executed by Google Cloud Functions.
    
    This is the entry point for the Cloud Function. It orchestrates the entire
    ETL process:
    1. Extracts complete data for each of the 10 diseases
    2. Combines all disease data into one DataFrame
    3. Cleans and standardizes the data (phases, dates, etc.)
    4. Loads data into Supabase in batches
    
    Args:
        event: Cloud Function event object (contains Pub/Sub message)
        context: Cloud Function context object (metadata about execution)
        
    Note:
        - Triggered by Cloud Scheduler via Pub/Sub topic
        - All errors are logged and execution continues
        - Data is upserted (inserted or updated) to handle re-runs
        - Batch processing prevents timeout and memory issues
    """
    
    log_message("ETL STARTED")

    try:
        # Initialize list to hold DataFrames for each disease
        all_dfs = []

        # Extract complete data for each disease
        # This loop processes all 10 diseases sequentially
        for disease, query in DISEASES.items():
            df = extract_combined_data(disease, query)
            if df is not None:
                all_dfs.append(df)

        # Combine all disease DataFrames into a single DataFrame
        # ignore_index=True means we create a new index (0, 1, 2, ...)
        df_combined = pd.concat(all_dfs, ignore_index=True)

        # Remove any duplicate trials that may exist across diseases
        # Some trials may be relevant to multiple diseases
        df_combined = df_combined.drop_duplicates(subset=['nctid'])

        # Log total records after combining all diseases
        log_message(f"Total extracted: {len(df_combined)}")

        # ====================================================================
        # DATA CLEANING AND TRANSFORMATION
        # ====================================================================

        # Standardize phase values to uppercase for consistent filtering
        # Phases may come as "Phase 1", "PHASE1", "phase1", etc.
        df_combined["phase"] = df_combined["phase"].str.upper().str.strip()

        # Define valid phase values
        # We only want trials in recognized phases (Phase 1 through Phase 4)
        valid_phases = ['PHASE1', 'PHASE2', 'PHASE3', 'PHASE4']
        
        # Filter DataFrame to keep only rows with valid phases
        # This removes any trials with unrecognized phase designations
        df_combined = df_combined[df_combined['phase'].isin(valid_phases)]

        # Log how many records remain after phase filtering
        log_message(f"After phase filter: {len(df_combined)}")

        # ====================================================================
        # CLEAN TEXT FIELDS
        # ====================================================================

        # Remove newlines and extra spaces from text fields
        # This prevents formatting issues in the database
        text_columns = [
            'briefsummary', 'detaileddescription', 'keywords',
            'primaryoutcomes', 'secondaryoutcomes'
        ]
        
        for col in text_columns:
            if col in df_combined.columns:
                # Remove newline characters
                df_combined[col] = df_combined[col].str.replace('\n', ' ', regex=False)
                # Remove carriage returns
                df_combined[col] = df_combined[col].str.replace('\r', ' ', regex=False)
                # Remove multiple spaces and replace with single space
                df_combined[col] = df_combined[col].str.replace('  ', ' ', regex=False)

        # Replace all N/A values with "Unknown"
        df_combined = df_combined.replace('N/A', 'Unknown')

        log_message("Text fields cleaned")

        
        # ====================================================================
        # DATA LOADING TO SUPABASE
        # ====================================================================

        # Create a Supabase client connection
        # This client will be used to communicate with the PostgreSQL database
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # TRUNCATE TABLE before loading to avoid duplicate key conflicts
        # This ensures clean data - no old essais from previous runs
        try:
            supabase.table('clinical_trials_combined').delete().neq('nctid', '').execute()
            log_message("Table truncated - ready for fresh load")
        except Exception as e:
            log_message(f"Warning: Could not truncate table: {e}")

        # Convert DataFrame to list of dictionaries for Supabase
        # Each row becomes a dictionary with column names as keys
        records = df_combined.to_dict(orient="records")

        # Define batch size for database inserts
        # Batching prevents timeouts and memory issues with large datasets
        BATCH_SIZE = 200

        # Process records in batches
        # This loop sends data to Supabase in chunks of 200 records
        for i in range(0, len(records), BATCH_SIZE):
            # Extract current batch of records
            batch = records[i:i+BATCH_SIZE]

            try:
                # Upsert (insert or update) batch to Supabase
                # "Upsert" means: insert if new, update if exists
                # This handles re-runs gracefully - no duplicate key errors
                supabase.table('clinical_trials_combined') \
                    .upsert(batch, ignore_duplicates=False) \
                    .execute()

                # Log successful batch insertion
                log_message(f"Batch {i//BATCH_SIZE + 1} inserted: {len(batch)} records")

            except Exception as e:
                # Log error but continue processing other batches
                # This ensures we don't lose all data if one batch fails
                log_message(f"Batch error: {e}")

        # Log final completion message with total records processed
        log_message(f"ETL COMPLETED: {len(records)} total records upserted")

    except Exception as e:
        # Catch and log any critical errors that crash the entire pipeline
        log_message(f"ETL FAILED: {e}")


# ============================================================================
# END OF SCRIPT
# ============================================================================