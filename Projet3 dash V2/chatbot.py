"""
chatbot.py — logique du chatbot (version simple sans markdown)
"""

from data import (
    fetch_active,
    disease_total_count,
    disease_active_count,
    disease_advanced_count,
)

# Questions disponibles
QUESTIONS = {
    "total_trials": "Combien d'essais au total ?",
    "active_trials": "Combien d'essais actifs ?",
    "advanced_trials": "Combien d'essais avancés ?",
    "sponsors": "Quels sponsors pharmaceutiques ?",
}


def answer_question(question_key: str, disease: str) -> str:
    """Retourne une réponse basée sur les données"""

    if not disease:
        return "Veuillez sélectionner une maladie."

    # =========================================================
    # TOTAL
    # =========================================================
    if question_key == "total_trials":
        n = disease_total_count(disease)
        return f"Il y a {n:,} essais cliniques au total pour {disease}."

    # =========================================================
    # ACTIFS
    # =========================================================
    if question_key == "active_trials":
        n = disease_active_count(disease)
        return f"Il y a {n:,} essais actuellement actifs pour {disease}."

    # =========================================================
    # AVANCÉS
    # =========================================================
    if question_key == "advanced_trials":
        n = disease_advanced_count(disease)
        return f"Il y a {n:,} essais en phase avancée (Phase II–IV) pour {disease}."

    # =========================================================
    # SPONSORS
    # =========================================================
    if question_key == "sponsors":
        df = fetch_active()

        key = disease.replace(" ", "_").lower()
        d = df[df["disease"].str.lower() == key]

        if d.empty:
            return f"Aucune donnée trouvée pour {disease}."

        pharma = (d["sponsortype"] == "INDUSTRY").sum()
        academic = (d["sponsortype"] != "INDUSTRY").sum()

        return (
            f"Pour {disease} :\n"
            f"- {pharma:,} essais sponsorisés par l'industrie pharmaceutique\n"
            f"- {academic:,} essais académiques"
        )

    # =========================================================
    return "Je ne comprends pas encore cette question."