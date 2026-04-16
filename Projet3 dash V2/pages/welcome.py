"""
pages/welcome.py — Hero + sélecteur + bouton About
Tous les IDs sont ici. Les callbacks sont dans app.py.
suppress_callback_exceptions=True permet leur enregistrement.
"""

from dash import html, dcc
from translations import t


def build_welcome_page(language: str = "English",
                       dis_options: list = None,
                       dis_default: str = None) -> html.Div:
    options = dis_options or []
    default = dis_default
    print(f"[welcome] options={options[:3] if options else 'VIDE'} default={default!r}")

    return html.Div([

        # ── Hero ──────────────────────────────────────────────
        html.Div([
            html.P(t("welcome_eyebrow", language), className="hero-eyebrow"),
            html.H1([
                t("welcome_line1", language), " ",
                html.Em(t("welcome_em", language)), " ",
                t("welcome_line2", language),
            ], className="hero-title"),
            html.P(t("welcome_subtitle", language), className="hero-subtitle"),
        ], className="hero-wrapper"),

        # ── Sélecteur maladie + Explorer ──────────────────────
        html.Div([
            html.P(t("explore_label", language), className="explore-label"),
            html.Div([
                dcc.Dropdown(
                    id="welcome-disease-selector",
                    options=options,
                    value=default,
                    placeholder=t("select_disease", language),
                    clearable=False,
                    className="welcome-disease-dropdown",
                    style={"color": "#050d1a"},
                ),
                html.Button(
                    t("explore_btn", language),
                    id="btn-welcome-explore",
                    n_clicks=0,
                    className="cta-btn explore-btn",
                ),
            ], className="explore-row"),
        ], className="explore-section"),

        # ── Bouton About ──────────────────────────────────────
        html.Div([
            html.Button(
                t("infos_btn", language),
                id="btn-go-infos",
                n_clicks=0,
                className="infos-btn",
            ),
        ], className="infos-btn-row"),

        html.Div(t("footer", language), className="ct-footer"),

    ], className="welcome-page")