"""
Airflow DAG for Clinical Trials ETL Pipeline
==============================================

This DAG orchestrates the clinical trials data extraction, transformation,
and loading process using Apache Airflow on Google Cloud Composer.

Schedule: Daily at 11:00 AM UTC (Monday-Friday)
Retries: 3 attempts with 5-minute delays
Timeout: 900 seconds (15 minutes)

The DAG:
1. Extracts clinical trial data from ClinicalTrials.gov API for 10 diseases
2. Transforms and cleans the data
3. Loads the processed data into Supabase PostgreSQL database

All credentials are stored securely in Cloud Composer environment variables.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to path so we can import main.py
# This assumes the DAG is in dags/ and main.py is in the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the ETL function from main.py
from dags.main import etl_combined, log_message


# ============================================================================
# DAG CONFIGURATION
# ============================================================================

# Default arguments applied to all tasks in the DAG
default_args = {
    # Owner of the DAG (for documentation and contact purposes)
    'owner': 'data-engineering',
    
    # Automatically retry failed tasks 3 times
    'retries': 3,
    
    # Wait 5 minutes between retry attempts
    'retry_delay': timedelta(minutes=5),
    
    # Email alerts on task failure (optional - configure if you have email setup)
    'email_on_failure': False,
    'email_on_retry': False,
    
    # Start date: when the DAG is first available for execution
    # Using a past date allows Airflow to schedule tasks immediately
    'start_date': datetime(2026, 4, 1),
    
    # Timeout for each task: 900 seconds = 15 minutes
    # This prevents tasks from hanging indefinitely
    'execution_timeout': timedelta(seconds=900),
}

# Define the DAG with all its parameters
dag = DAG(
    # Unique identifier for the DAG (used in Cloud Composer UI)
    dag_id='clinical_trials_etl_pipeline',
    
    # Human-readable description shown in Airflow UI
    description='Extract, transform, and load clinical trials data from ClinicalTrials.gov to Supabase',
    
    # Apply default arguments to all tasks
    default_args=default_args,
    
    # Schedule interval: cron expression for execution timing
    # Format: minute hour day-of-month month day-of-week
    # "0 11 * * 1-5" = Every weekday (Mon-Fri) at 11:00 AM UTC
    schedule_interval='0 11 * * 1-5',
    
    # Timezone for schedule interpretation
    # UTC is the default, change if your schedule should use a different timezone
    max_active_runs=1,  # Prevent multiple simultaneous runs
    
    # Do not catch up on missed runs
    # If Airflow is down for a few days, don't try to backfill all missed dates
    catchup=False,
    
    # Tags for organization in Airflow UI
    tags=['clinical-trials', 'etl', 'gcp', 'supabase'],
)


# ============================================================================
# PYTHON TASK FUNCTION
# ============================================================================

def run_etl():
    """
    Python function that executes the ETL pipeline.
    
    This function:
    1. Reads Supabase credentials from Cloud Composer environment variables
    2. Calls the etl_combined() function from main.py
    3. Logs the execution status
    
    Environment variables used (set in Cloud Composer):
    - SUPABASE_URL: Your Supabase project URL
    - SUPABASE_KEY: Your Supabase anonymous API key
    
    Returns:
        None
        
    Raises:
        Exception: Any errors are caught by Airflow and logged in the UI
    """
    
    log_message("="*80)
    log_message("Starting Clinical Trials ETL Pipeline")
    log_message("="*80)
    
    try:
        # Verify that Supabase credentials are available
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError(
                "Supabase credentials not found. "
                "Ensure SUPABASE_URL and SUPABASE_KEY are set in Cloud Composer environment."
            )
        
        log_message(f"Supabase URL: {supabase_url}")
        log_message("Supabase credentials loaded successfully")
        
        # Call the main ETL function
        # Note: event and context are not used in this context, but we pass None
        # to maintain compatibility with the Cloud Functions signature
        etl_combined(None, None)
        
        log_message("="*80)
        log_message("ETL Pipeline completed successfully")
        log_message("="*80)
        
    except Exception as e:
        log_message(f"ERROR: ETL Pipeline failed with error: {str(e)}")
        raise  # Re-raise the exception so Airflow marks the task as failed


# ============================================================================
# DEFINE AIRFLOW TASKS
# ============================================================================

# Create a single task that runs the ETL function
# PythonOperator executes a Python function with no external dependencies
etl_task = PythonOperator(
    # Unique task identifier within the DAG
    task_id='run_clinical_trials_etl',
    
    # The Python function to execute
    python_callable=run_etl,
    
    # Pass any exceptions to Airflow for proper error handling
    provide_context=True,
)


# ============================================================================
# DEFINE TASK DEPENDENCIES
# ============================================================================

# Since we only have one task, no dependencies needed
# If you add more tasks in the future, use:
# task1 >> task2  (task2 depends on task1)
# task1 >> task2 >> task3  (chain of dependencies)

# For now, just reference the task to tell Airflow it's part of the DAG
etl_task

# ============================================================================
# END OF DAG DEFINITION
# ============================================================================