"""
pages/infos.py — Stats, feature cards, phase legend
"""

from dash import html
from translations import t


def build_infos_page(language: str = "English") -> html.Div:
    return html.Div([

        html.Div([
            html.P(t("welcome_eyebrow", language), className="hero-eyebrow",
                   style={"textAlign": "left"}),
            html.H2([t("infos_title", language), " — Tracking Hope"], className="browse-title"),
            html.P(t("infos_subtitle", language), className="browse-subtitle"),
        ], className="browse-header"),

        html.Hr(className="ct-divider"),

        html.Div([
            _stat("480K+",     t("stat_trials",    language)),
            _stat("220+",      t("stat_countries", language)),
            _stat("4",         t("stat_phases",    language)),
            _stat("Real-time", t("stat_sync",      language)),
        ], className="stat-bar", style={"marginBottom": "2.5rem"}),

        html.Hr(className="ct-divider"),

        html.Div([
            _card(t("card_db_title",  language), t("card_db_desc",  language)),
            _card(t("card_tl_title",  language), t("card_tl_desc",  language)),
            _card(t("card_al_title",  language), t("card_al_desc",  language)),
            _card(t("card_cp_title",  language), t("card_cp_desc",  language)),
            _card(t("card_api_title", language), t("card_api_desc", language)),
            _card(t("card_cmp_title", language), t("card_cmp_desc", language)),
        ], className="cards-grid"),

        html.Div([
            html.Span(t("phase1",     language), className="phase-badge p1"),
            html.Span(t("phase2",     language), className="phase-badge p2"),
            html.Span(t("phase3",     language), className="phase-badge p3"),
            html.Span(t("phase4",     language), className="phase-badge p4"),
            html.Span(t("nct_lookup", language), className="phase-badge nct"),
        ], className="phase-legend"),

        html.Div(t("footer", language), className="ct-footer"),

    ], className="browse-page")


def _stat(value, label):
    return html.Div([
        html.Div(value, className="stat-value"),
        html.Div(label, className="stat-label"),
    ], className="stat-item")


def _card(title, desc):
    return html.Div([
        html.Div(title, className="card-title"),
        html.Div(desc,  className="card-desc"),
    ], className="feature-card")