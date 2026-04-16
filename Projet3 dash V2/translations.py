import json
import os
import threading
from deep_translator import GoogleTranslator

SOURCE_LANG = "en"

SUPPORTED_LANGUAGES = {
    "English":   "en",
    "Français":  "fr",
    "Español":   "es",
    "Deutsch":   "de",
    "Italiano":  "it",
    "中文":       "zh-CN",
    "العربية":   "ar",
    "Português": "pt",
}

LANG_CODES = {
    "English":   "EN",
    "Français":  "FR",
    "Español":   "ES",
    "Deutsch":   "DE",
    "Italiano":  "IT",
    "中文":       "ZH",
    "العربية":   "AR",
    "Português": "PT",
}

RTL_LANGUAGES = {"العربية"}

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translation_cache.json")
META_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translation_meta.json")
_cache_lock = threading.Lock()


def _load_cache():
    if os.path.exists(META_FILE):
        with open(META_FILE, encoding="utf-8") as f:
            if json.load(f).get("source_lang") != SOURCE_LANG:
                _reset_cache()
                return {}
    else:
        _write_meta()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _reset_cache():
    _write_meta()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)


def _write_meta():
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump({"source_lang": SOURCE_LANG}, f)


def _save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


_memory_cache = _load_cache()

UI_TEXTS = {
    # ── Settings ─────────────────────────────────────────────
    "settings_title": "Settings",
    "appearance":     "Appearance",
    "dark_mode":      "Dark mode",
    "light_mode":     "Light mode",
    "favorites":      "Favorite studies",
    "no_favorites":   "No favorite studies yet.",
    "remove":         "Remove",
    "logout":         "Logout",
    "logout_btn":     "Log out",
    "logout_confirm": "You have been logged out.",

    # ── Navigation ───────────────────────────────────────────
    "nav_home":       "Home",

    # ── Welcome ──────────────────────────────────────────────
    "welcome_eyebrow": "Powered by ClinicalTrials.gov API",
    "welcome_line1":   "Track",
    "welcome_em":      "every",
    "welcome_line2":   "step of the research.",
    "welcome_subtitle": (
        "Aggregates live clinical-trial data into a focused database, "
        "so you can monitor drug development from Phase I to approval — "
        "all in one place."
    ),
    "explore_label":   "Select a disease and explore its clinical trials",
    "explore_btn":     "Explore",
    "select_disease":  "Select a disease...",
    "infos_btn":       "About this app",

    # ── Infos page ───────────────────────────────────────────
    "infos_title":    "About",
    "infos_subtitle": "A research tool aggregating live clinical trial data from ClinicalTrials.gov.",
    "stat_trials":    "Registered Trials",
    "stat_countries": "Countries",
    "stat_phases":    "Clinical Phases Tracked",
    "stat_sync":      "Real-time API Sync",
    "card_db_title":  "Selective Database",
    "card_db_desc":   (
        "Build and curate a focused subset of ClinicalTrials.gov, filtered by "
        "therapeutic area, compound, or sponsor."
    ),
    "card_tl_title":  "Progress Timeline",
    "card_tl_desc":   (
        "Visualise a drug's journey across phases with interactive milestone "
        "timelines and status-change history."
    ),
    "card_al_title":  "Status Alerts",
    "card_al_desc":   (
        "Get notified when a tracked compound advances, is suspended, or "
        "publishes new results."
    ),
    "card_cp_title":  "Compound Profiles",
    "card_cp_desc":   (
        "Deep-dive pages per drug: all active & completed trials, endpoints, "
        "enrolment figures, and sponsor details."
    ),
    "card_api_title": "Live API Sync",
    "card_api_desc":  (
        "Pulls directly from the ClinicalTrials.gov v2 API — your database "
        "stays current without manual updates."
    ),
    "card_cmp_title": "Comparative Analysis",
    "card_cmp_desc":  (
        "Side-by-side phase distribution and enrolment comparisons across "
        "compounds or therapeutic classes."
    ),
    "phase1":         "Phase I — Safety",
    "phase2":         "Phase II — Efficacy",
    "phase3":         "Phase III — Pivotal",
    "phase4":         "Phase IV — Post-market",
    "nct_lookup":     "NCT ID lookup",

    # ── Disease page ─────────────────────────────────────────
    "disease_active":      "Active trials",
    "disease_phase_title": "Phase distribution",
    "disease_phase_desc":  "Breakdown of active studies by clinical phase.",
    "disease_time_title":  "Trials over time",
    "disease_time_desc":   "Number of active studies started each year since 2010.",
    "disease_geo_title":   "Geographic distribution",
    "disease_geo_desc":    "Countries conducting active trials for this disease.",
    "top5_title":          "Top 5 most promising active studies",
    "top5_desc":           (
        "Ranked by Promise Score: phase, results published, industry sponsor, "
        "FDA regulation, and enrollment weighted by regulatory region."
    ),
    "sidebar_disease":  "Disease",
    "sidebar_explore":  "Explore",

    # ── Auth ─────────────────────────────────────────────────
    "account":            "Account",
    "login_title":        "Sign in",
    "register_title":     "Create account",
    "login_btn":          "Sign in",
    "register_btn":       "Create account",
    "login_link":         "Sign in",
    "register_link":      "Create an account",
    "no_account":         "No account yet?",
    "has_account":        "Already have an account?",
    "email_label":        "Email",
    "email_placeholder":  "your@email.com",
    "password_label":     "Password",
    "password_placeholder": "••••••••",
    "name_label":         "Full name",
    "name_placeholder":   "John Doe",
    "auth_error_fields":  "Please fill in all required fields.",
    "logged_as":          "Signed in as",
    "logout_confirm":     "You have been signed out.",

    # ── Shared ───────────────────────────────────────────────
    "no_results":   "No results found.",
    "participants": "Participants",
    "phase":        "Phase",
    "intervention": "Intervention",
    "region":       "Region",
    "score":        "Score",
    "footer":       (
        "Data source: ClinicalTrials.gov · NLM / NIH · "
        "Tracking Hope is a research tool and not a medical resource."
    ),
}


def translate(text: str, lang: str) -> str:
    code = SUPPORTED_LANGUAGES.get(lang, "en")
    if code == SOURCE_LANG:
        return text
    key = f"{code}::{text}"
    with _cache_lock:
        if key in _memory_cache:
            return _memory_cache[key]
    try:
        result = GoogleTranslator(source=SOURCE_LANG, target=code).translate(text)
        if not result:
            return text
    except Exception:
        return text
    with _cache_lock:
        _memory_cache[key] = result
        _save_cache(_memory_cache)
    return result


def is_rtl(lang: str) -> bool:
    return lang in RTL_LANGUAGES


def t(key: str, lang: str) -> str:
    return translate(UI_TEXTS.get(key, key), lang)


def _preload():
    texts = list(UI_TEXTS.values())
    for lang_name, code in SUPPORTED_LANGUAGES.items():
        if code == SOURCE_LANG:
            continue
        with _cache_lock:
            missing = [tx for tx in texts if f"{code}::{tx}" not in _memory_cache]
        if not missing:
            continue
        try:
            tr  = GoogleTranslator(source=SOURCE_LANG, target=code)
            res = {}
            for tx in missing:
                out = tr.translate(tx)
                if out:
                    res[f"{code}::{tx}"] = out
            with _cache_lock:
                _memory_cache.update(res)
                _save_cache(_memory_cache)
            print(f"[translations] {lang_name} OK ({len(res)} texts)")
        except Exception as e:
            print(f"[translations] {lang_name} error: {e}")


threading.Thread(target=_preload, daemon=True).start()