"""
Clinical Trials ETL Pipeline
=============================

This module implements an Extract-Transform-Load (ETL) pipeline that:
1. Extracts clinical trial data from ClinicalTrials.gov API for 10 diseases
2. Transforms and cleans the data (remove duplicates, standardize phases, etc.)
3. Loads the processed data into Supabase PostgreSQL database

The pipeline is designed to run automatically via Google Cloud Functions
and Cloud Scheduler, executing daily at 11:00 AM UTC (Monday-Friday).

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
    Extract clinical trial data from ClinicalTrials.gov API for a specific disease.
    
    This function:
    1. Sends paginated requests to the API using the disease search query
    2. Extracts relevant trial information from each study
    3. Handles pagination to retrieve all available results
    4. Removes duplicate studies based on NCTId
    5. Returns a pandas DataFrame with the cleaned data
    
    Args:
        disease_name (str): Name of the disease (e.g., 'Hypertension')
        search_query (str): API search query with disease keywords
        
    Returns:
        pd.DataFrame: DataFrame with trial data or None if extraction fails
        
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

                # Extract different sections of the protocol
                ident = protocol.get('identificationModule', {})  # Trial ID, title
                status_mod = protocol.get('statusModule', {})  # Status, dates
                design_mod = protocol.get('designModule', {})  # Phase, design details
                desc_mod = protocol.get('descriptionModule', {})  # Summary, description
                sponsor_mod = protocol.get('sponsorCollaboratorsModule', {})  # Sponsors
                locations_mod = protocol.get('contactsLocationsModule', {})  # Locations

                # Extract trial phases and convert to string
                # Phases indicate the development stage of the trial (I, II, III, IV)
                phases = design_mod.get('phases', [])
                phase = ", ".join(phases) if phases else 'N/A'

                # Extract trial locations and extract unique country names
                locations = locations_mod.get('locations', [])
                countries = list(set(loc.get('country') for loc in locations if loc.get('country')))
                countries_str = ", ".join(countries)

                # Create a record (dictionary) with the extracted trial information
                # All keys are lowercase to match Supabase column names
                all_data.append({
                    'disease': disease_name,  # Which disease this trial is for
                    'nctid': ident.get('nctId'),  # National Clinical Trial ID (unique identifier)
                    'title': ident.get('briefTitle'),  # Brief title of the trial
                    'status': status_mod.get('overallStatus'),  # Current status (recruiting, completed, etc.)
                    'phase': phase,  # Trial phase (I, II, III, IV)
                    'startdate': status_mod.get('startDateStruct', {}).get('date'),  # When trial started
                    'locations': countries_str,  # Countries where trial is conducted
                    'briefsummary': desc_mod.get('briefSummary', 'N/A'),  # Brief description of trial
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
    1. Extracts data for each of the 10 diseases
    2. Combines all disease data into one DataFrame
    3. Cleans and standardizes the data
    4. Loads data into Supabase in batches
    
    Args:
        event: Cloud Function event object (contains Pub/Sub message)
        context: Cloud Function context object (metadata about execution)
        
    Note:
        - Triggered by Cloud Scheduler via Pub/Sub topic
        - All errors are logged and execution continues
        - Data is upserted (inserted or updated) to handle re-runs
    """
    
    log_message("ETL STARTED")

    try:
        # Initialize list to hold DataFrames for each disease
        all_dfs = []

        # Extract data for each disease
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
        # DATA LOADING TO SUPABASE
        # ====================================================================

        # Create a Supabase client connection
        # This client will be used to communicate with the PostgreSQL database
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
                    .upsert(batch) \
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