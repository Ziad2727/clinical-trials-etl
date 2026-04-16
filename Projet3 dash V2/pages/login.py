"""
pages/login.py — Page de connexion / inscription
Le mode login/register est géré par store-auth-mode sans reconstruire la page.
"""

from dash import html, dcc
from translations import t


def build_login_page(language: str = "English", mode: str = "login") -> html.Div:
    is_register = mode == "register"

    return html.Div([

        # Header
        html.Div([
            html.P(t("welcome_eyebrow", language), className="hero-eyebrow",
                   style={"textAlign": "center", "marginBottom": "0.6rem"}),
            html.H2(id="auth-title",
                    children=t("register_title", language) if is_register else t("login_title", language),
                    className="browse-title",
                    style={"textAlign": "center", "marginBottom": "1.5rem"}),
        ]),

        # Carte
        html.Div([

            html.Div([
                html.Label(t("email_label", language), className="auth-label"),
                dcc.Input(id="auth-email", type="email",
                          placeholder=t("email_placeholder", language),
                          className="auth-input", debounce=False),
            ], className="auth-field"),

            html.Div([
                html.Label(t("password_label", language), className="auth-label"),
                dcc.Input(id="auth-password", type="password",
                          placeholder=t("password_placeholder", language),
                          className="auth-input", debounce=False),
            ], className="auth-field"),

            html.Div(id="auth-message", className="auth-message"),

            html.Button(
                id="btn-auth-submit", n_clicks=0,
                children=t("register_btn", language) if is_register else t("login_btn", language),
                className="auth-submit-btn",
            ),

            html.Hr(className="ct-divider", style={"margin": "1.2rem 0"}),

            html.Div([
                html.Span(id="auth-switch-text",
                          children=t("no_account", language) if not is_register else t("has_account", language),
                          className="auth-switch-text"),
                html.Button(
                    id="btn-auth-switch", n_clicks=0,
                    children=t("register_link", language) if not is_register else t("login_link", language),
                    className="auth-switch-btn",
                ),
            ], className="auth-switch-row"),

        ], className="auth-card"),

    ], className="auth-page")