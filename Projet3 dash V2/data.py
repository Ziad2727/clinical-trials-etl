"""
data.py — Supabase data layer + scoring
"""

import os
import numpy as np
import pandas as pd
from supabase import create_client, Client

# ── Connexion ─────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://cmvnwgmcbmhpldluycya.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNtdm53Z21jYm1ocGxkbHV5Y3lhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ1MTg1MTcsImV4cCI6MjA5MDA5NDUxN30.6OEr3mUJqBgUGRJ1DtLd-awfTVVyV1WZ-1PpL-xTqMA")
TABLE        = "clinical_trials_combined"

ACTIVE_STATUSES = [
    "RECRUITING", "ACTIVE_NOT_RECRUITING",
    "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING",
]

_df_cache = None


def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_all() -> pd.DataFrame:
    """Toutes les études — mis en cache après le premier appel."""
    global _df_cache
    if _df_cache is not None:
        return _df_cache

    client = get_client()
    rows, offset, page = [], 0, 1000
    while True:
        batch = (
            client.table(TABLE)
            .select("*")
            .range(offset, offset + page - 1)
            .execute()
            .data
        )
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page:
            break
        offset += page

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    str_cols = [
        "nctid", "title", "conditions", "phase", "status",
        "interventionname", "primarypurpose", "sponsortype",
        "locations", "startdate", "enddate", "disease",
    ]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].fillna("N/A").astype(str)

    if "enrollment"     in df.columns:
        df["enrollment"]     = pd.to_numeric(df["enrollment"], errors="coerce").fillna(0)
    if "hasresults"     in df.columns:
        df["hasresults"]     = df["hasresults"].astype(bool)
    if "isfdaregulated" in df.columns:
        df["isfdaregulated"] = df["isfdaregulated"].astype(bool)
    if "startdate"      in df.columns:
        df["startyear"] = pd.to_datetime(df["startdate"], errors="coerce").dt.year

    _df_cache = df
    return df


def fetch_active() -> pd.DataFrame:
    return fetch_all()[fetch_all()["status"].isin(ACTIVE_STATUSES)].copy()


def get_disease_list() -> list:
    df = fetch_all()
    return sorted([d.replace("_", " ") for d in df["disease"].dropna().unique()])


# ── Région ────────────────────────────────────────────────────
HIGH_REG = {
    "United States", "Germany", "France", "United Kingdom", "Spain", "Italy",
    "Netherlands", "Belgium", "Sweden", "Denmark", "Norway", "Finland",
    "Austria", "Switzerland", "Canada", "Australia", "Japan", "Ireland",
    "Portugal", "Poland", "Czech Republic", "Israel", "Czechia",
}
MED_REG = {
    "Brazil", "India", "South Korea", "Mexico", "Turkey", "Argentina",
    "Thailand", "Malaysia", "South Africa", "Colombia", "Chile", "Hungary",
    "Romania", "Ukraine", "Greece", "Bulgaria", "Taiwan",
}


def classify_region(loc: str):
    if not loc or loc == "N/A":
        return "LOW", 0.3
    countries = {c.strip() for c in loc.split(",")}
    if countries & HIGH_REG:
        return "HIGH", 1.0
    if countries & MED_REG:
        return "MED", 0.6
    return "LOW", 0.3


# ── Scoring ───────────────────────────────────────────────────
VALID_PHASES      = ["PHASE2", "PHASE3", "PHASE4"]
EXCLUDED_PURPOSES = ["BASIC_SCIENCE", "HEALTH_SERVICES_RESEARCH", "DEVICE_FEASIBILITY"]


def _phase_score(p: str) -> int:
    if "PHASE4" in p: return 40
    if "PHASE3" in p: return 30
    if "PHASE2" in p: return 15
    return 0


def _enroll_score(n: float, w: float) -> float:
    if n <= 0:
        return 0.0
    return round(min(15, 15 * np.log10(max(n, 1)) / np.log10(10000)) * w, 1)


def _score(d: pd.DataFrame) -> pd.DataFrame:
    if d.empty:
        return d
    d = d.copy()
    reg            = d["locations"].apply(classify_region)
    d["region"]    = reg.apply(lambda x: x[0])
    d["regweight"] = reg.apply(lambda x: x[1])
    d["s_phase"]   = d["phase"].apply(_phase_score)
    d["s_results"] = d["hasresults"].apply(lambda x: 20 if x else 0)
    d["s_sponsor"] = d["sponsortype"].apply(lambda x: 20 if x == "INDUSTRY" else 0)
    d["s_fda"]     = d["isfdaregulated"].apply(lambda x: 10 if x else 0)
    d["s_enroll"]  = d.apply(lambda r: _enroll_score(r["enrollment"], r["regweight"]), axis=1)
    d["score"]     = d[["s_phase", "s_results", "s_sponsor", "s_fda", "s_enroll"]].sum(axis=1)
    return d


def top5_for_disease(disease: str) -> pd.DataFrame:
    key = disease.replace(" ", "_")
    df  = fetch_active()
    d   = df[df["disease"].str.lower() == key.lower()].copy()
    if d.empty:
        return d
    d = d[d["phase"].apply(lambda p: any(ph in p for ph in VALID_PHASES))]
    d = d[~d["primarypurpose"].isin(EXCLUDED_PURPOSES)]
    if d.empty:
        return d
    if len(d) >= 10:
        reg_s = d["locations"].apply(classify_region).apply(lambda x: x[0])
        def top75(g):
            return g[g["enrollment"] >= g["enrollment"].quantile(0.25)]
        d = d.groupby(reg_s, group_keys=False).apply(top75).reset_index(drop=True)
    return _score(d).sort_values("score", ascending=False).head(5)


# ── KPIs par maladie ─────────────────────────────────────────

def _disease_df(disease: str) -> pd.DataFrame:
    key = disease.replace(" ", "_")
    df  = fetch_active()
    return df[df["disease"].str.lower() == key.lower()].copy()


def disease_total_count(disease: str) -> int:
    """Toutes les études extraites"""
    df = fetch_all()
    key = disease.replace(" ", "_")
    return len(df[df["disease"].str.lower() == key.lower()])


def disease_active_count(disease: str) -> int:
    """Phase 1-4 + status actif"""
    df = fetch_active()
    key = disease.replace(" ", "_")
    d = df[df["disease"].str.lower() == key.lower()]
    d = d[d["phase"].str.upper().apply(
        lambda p: any(ph in str(p) for ph in ["PHASE1", "PHASE2", "PHASE3", "PHASE4"])
    )]
    return len(d)

def disease_advanced_count(disease: str) -> int:
    """Compte les études après filtres (phase valide + purpose valide)"""
    key = disease.replace(" ", "_")
    df = fetch_active()
    d = df[df["disease"].str.lower() == key.lower()].copy()
    
    # Appliquez les mêmes filtres que dans top5_for_disease
    d = d[d["phase"].apply(lambda p: any(ph in p for ph in ["PHASE2", "PHASE3", "PHASE4"]))]
    d = d[~d["primarypurpose"].isin(["BASIC_SCIENCE", "HEALTH_SERVICES_RESEARCH", "DEVICE_FEASIBILITY"])]
    
    return len(d)

def disease_phase_dist(disease: str) -> pd.DataFrame:
    return _phase_counts(_disease_df(disease))


def disease_trials_per_year(disease: str) -> pd.DataFrame:
    d = _disease_df(disease).copy()
    d["startyear"] = pd.to_datetime(d["startdate"], errors="coerce").dt.year
    by = d.dropna(subset=["startyear"]).groupby("startyear").size().reset_index(name="Count")
    by = by[by["startyear"] >= 2010]
    by["startyear"] = by["startyear"].astype(int)
    return by


def disease_geo(disease: str) -> pd.DataFrame:
    d   = _disease_df(disease)
    exp = d["locations"].str.split(",").explode().str.strip()
    exp = exp[exp != "N/A"]
    counts = exp.value_counts().reset_index()
    counts.columns = ["Country", "Count"]
    return counts


# ── KPIs globaux ─────────────────────────────────────────────

def _phase_counts(df: pd.DataFrame) -> pd.DataFrame:
    phase_map = {
        "PHASE1": "Phase I", "PHASE2": "Phase II",
        "PHASE3": "Phase III", "PHASE4": "Phase IV",
        "EARLY_PHASE1": "Early Phase I",
    }
    def ep(p):
        for k, v in phase_map.items():
            if k in p: return v
        return "N/A"
    counts = df["phase"].apply(ep).value_counts().reset_index()
    counts.columns = ["Phase", "Count"]
    order = ["Early Phase I", "Phase I", "Phase II", "Phase III", "Phase IV", "N/A"]
    counts["Phase"] = pd.Categorical(counts["Phase"], categories=order, ordered=True)
    return counts.sort_values("Phase")
