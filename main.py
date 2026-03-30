import base64
import requests
import time
from datetime import datetime
import os
from supabase import create_client

API_URL = "https://clinicaltrials.gov/api/v2/studies"
STATUS_FILTER = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,COMPLETED"
PAGE_SIZE = 1000

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def log(msg):
    print(f"[{datetime.now()}] {msg}")

def etl_trials(event, context):
    log("START ETL")

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        params = {
            "query.cond": "Diabetes",
            "filter.overallStatus": STATUS_FILTER,
            "pageSize": PAGE_SIZE
        }

        all_trials = []

        response = requests.get(API_URL, params=params, timeout=15)
        data = response.json()

        studies = data.get("studies", [])

        for study in studies:
            protocol = study.get("protocolSection", {})
            ident = protocol.get("identificationModule", {})
            status_mod = protocol.get("statusModule", {})
            design_mod = protocol.get("designModule", {})

            trial = {
                "NCTId": ident.get("nctId"),
                "Title": ident.get("briefTitle"),
                "Status": status_mod.get("overallStatus"),
                "Phase": ", ".join(design_mod.get("phases", [])) or "Unknown"
            }

            if trial["NCTId"]:
                all_trials.append(trial)

        log(f"{len(all_trials)} trials fetched")

        # 🔥 nettoyage sans pandas
        unique_trials = {t["NCTId"]: t for t in all_trials}.values()

        # 🔥 batch insert
        supabase.table("clinical_trials").upsert(list(unique_trials)).execute()

        log("UPLOAD OK")

    except Exception as e:
        log(f"ERROR: {e}")
        raise