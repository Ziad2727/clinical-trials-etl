"""
app.py — Tracking Hope
Navigation via dcc.Location pour activer les flèches du navigateur.
"""

import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import json

from translations import t, is_rtl, LANG_CODES
import settings
from chatbot_ui import build_chatbot


app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Tracking Hope",
    use_pages=False,
)

try:
    from data import get_disease_list
    _diseases    = get_disease_list()
    _dis_options = [{"label": d, "value": d} for d in _diseases]
    _dis_default = _diseases[0] if _diseases else None
    print(f"[startup] {len(_diseases)} maladies: {_diseases}")
except Exception as e:
    import traceback; traceback.print_exc()
    _diseases, _dis_options, _dis_default = [], [], None

# Mapping page <-> pathname URL
PAGE_TO_PATH = {
    "welcome":   "/",
    "disease":   "/disease",
    "infos":     "/infos",
    "login":     "/login",
    "favorites": "/favorites",
}
PATH_TO_PAGE = {v: k for k, v in PAGE_TO_PATH.items()}


app.layout = html.Div([

    # ── Location (gère l'URL et l'historique du navigateur) ───
    dcc.Location(id="url", refresh=False),

    # ── Stores ────────────────────────────────────────────────
    dcc.Store(id="store-language",      storage_type="session", data="English"),
    dcc.Store(id="store-dark-mode",     storage_type="session", data=False),
    dcc.Store(id="store-favorites",     storage_type="session", data=[]),
    dcc.Store(id="store-settings-open", storage_type="memory",  data=False),
    dcc.Store(id="store-disease",       storage_type="memory",  data=_dis_default),
    dcc.Store(id="store-user",          storage_type="session", data=None),
    dcc.Store(id="store-auth-mode",     storage_type="memory",  data="login"),
    dcc.Store(id="store-top5-data", storage_type="memory"),
    # ── Header ────────────────────────────────────────────────
    html.Div([
        html.Div(
            html.Img(
                src="/assets/logo.png",
                className="header-logo",
                id="btn-home",
                alt="Tracking Hope",
            ),
            className="header-brand", style={"cursor": "pointer"},
        ),
        html.Div([
            html.Button("Home", id="btn-nav-home", n_clicks=0,
                        className="nav-btn", style={"display": "none"}),
            html.Button("♡ Favoris", id="btn-nav-favorites", n_clicks=0,
                        className="nav-btn fav-nav-btn"),

            # ── Langue ────────────────────────────────────────
            html.Div([
                html.Button("EN", id="btn-lang", n_clicks=0, className="lang-btn"),
                html.Div(id="lang-menu", className="lang-menu hidden", children=[
                    html.Button(f"{lang} ({code})",
                                id={"type": "btn-lang-option", "value": lang},
                                n_clicks=0, className="lang-option")
                    for lang, code in LANG_CODES.items()
                ]),
            ], className="lang-wrapper"),

            # ── Settings ──────────────────────────────────────
            html.Div([
                html.Button(html.Span("⚙", className="gear-icon"),
                            id="btn-settings", n_clicks=0, className="settings-btn"),
                html.Div(
                    settings.build_settings_panel("English", False, [], None),
                    id="settings-panel", className="settings-panel hidden",
                ),
            ], className="settings-wrapper"),
        ], className="header-actions"),
    ], className="app-header"),

    html.Hr(className="ct-divider header-divider"),

    # ── Body ──────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Div([
                html.Div(id="main-content"),

                # Page login cachée par défaut
                html.Div([
                    html.Div([
                        html.P("Powered by ClinicalTrials.gov API", id="auth-eyebrow",
                               className="hero-eyebrow", style={"textAlign":"center","marginBottom":"0.6rem"}),
                        html.H2("Sign in", id="auth-title", className="browse-title",
                                style={"textAlign":"center","marginBottom":"1.5rem"}),
                    ]),
                    html.Div([
                        html.Div([
                            html.Label("Email", id="auth-email-label", className="auth-label"),
                            dcc.Input(id="auth-email", type="email",
                                      placeholder="your@email.com",
                                      className="auth-input", debounce=False),
                        ], className="auth-field"),
                        html.Div([
                            html.Label("Password", id="auth-password-label", className="auth-label"),
                            dcc.Input(id="auth-password", type="password",
                                      placeholder="••••••••",
                                      className="auth-input", debounce=False),
                        ], className="auth-field"),
                        html.Div(id="auth-message", className="auth-message"),
                        html.Button("Sign in", id="btn-auth-submit", n_clicks=0,
                                    className="auth-submit-btn"),
                        html.Hr(className="ct-divider", style={"margin":"1.2rem 0"}),
                        html.Div([
                            html.Span("No account yet?", id="auth-switch-text",
                                      className="auth-switch-text"),
                            html.Button("Create an account", id="btn-auth-switch",
                                        n_clicks=0, className="auth-switch-btn"),
                        ], className="auth-switch-row"),
                    ], className="auth-card"),
                ], id="login-page", className="auth-page", style={"display":"none"}),

            ], className="main-area", id="main-area-wrapper"),
        ], className="body-row"),
    ], id="app-root"),
    build_chatbot(),
], id="page-wrapper")


# ============================================================
# ROUTEUR PRINCIPAL — piloté par l'URL
# ============================================================
@callback(
    Output("main-content", "children"),
    Output("login-page",   "style"),
    Output("btn-nav-home", "style"),
    Input("url",           "pathname"),
    Input("store-language","data"),
    State("store-disease", "data"),
)
def route_page(pathname, language, disease):
    import traceback
    page = PATH_TO_PAGE.get(pathname, "welcome")
    HOME_ON   = {"display": "inline-flex"}
    HOME_OFF  = {"display": "none"}
    LOGIN_ON  = {"display": "flex", "flexDirection": "column", "alignItems": "center"}
    LOGIN_OFF = {"display": "none"}
    try:
        if page == "welcome":
            from pages.welcome import build_welcome_page
            return build_welcome_page(language, _dis_options, _dis_default), LOGIN_OFF, HOME_OFF

        elif page == "infos":
            from pages.infos import build_infos_page
            return build_infos_page(language), LOGIN_OFF, HOME_ON

        elif page == "disease":
            from pages.disease import build_disease_page
            d = disease or (_diseases[0] if _diseases else "")
            return build_disease_page(d, language, _dis_options), LOGIN_OFF, HOME_ON

        elif page == "login":
            return html.Div(), LOGIN_ON, HOME_ON

        elif page == "favorites":
            from pages.favorites import build_favorites_page
            return build_favorites_page(language), LOGIN_OFF, HOME_ON

        from pages.welcome import build_welcome_page
        return build_welcome_page(language, _dis_options, _dis_default), LOGIN_OFF, HOME_OFF

    except Exception as e:
        traceback.print_exc()
        return html.Div(f"Erreur : {e}", style={"color":"#d94040","fontFamily":"monospace","padding":"2rem"}), LOGIN_OFF, HOME_OFF


# ============================================================
# NAVIGATION — tous les boutons mettent à jour l'URL
# ============================================================
@callback(
    Output("url", "pathname"),
    Input("btn-home",          "n_clicks"),
    Input("btn-nav-home",      "n_clicks"),
    Input("btn-nav-favorites", "n_clicks"),
    prevent_initial_call=True,
)
def navigate(n_home, n_nav_home, n_favorites):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if btn_id in ("btn-home", "btn-nav-home"):
        return "/"
    if btn_id == "btn-nav-favorites":
        return "/favorites"
    return dash.no_update


@callback(
    Output("url",           "pathname", allow_duplicate=True),
    Output("store-disease", "data",     allow_duplicate=True),
    Input("btn-welcome-explore",      "n_clicks"),
    State("welcome-disease-selector", "value"),
    prevent_initial_call=True,
)
def on_welcome_explore(n, disease):
    if not n or not disease:
        return dash.no_update, dash.no_update
    return "/disease", disease


@callback(
    Output("url", "pathname", allow_duplicate=True),
    Input("btn-go-infos", "n_clicks"),
    prevent_initial_call=True,
)
def on_go_infos(n):
    return "/infos" if n else dash.no_update


@callback(
    Output("url",           "pathname", allow_duplicate=True),
    Output("store-disease", "data",     allow_duplicate=True),
    Input("btn-disease-explore",   "n_clicks"),
    State("disease-page-selector", "value"),
    prevent_initial_call=True,
)
def on_disease_explore(n, disease):
    if not n or not disease:
        return dash.no_update, dash.no_update
    return "/disease", disease


# ============================================================
# LOGIN PAGE — basculer login ↔ register
# ============================================================
@callback(
    Output("store-auth-mode",  "data"),
    Output("auth-title",       "children"),
    Output("btn-auth-submit",  "children"),
    Output("auth-switch-text", "children"),
    Output("btn-auth-switch",  "children"),
    Input("btn-auth-switch",   "n_clicks"),
    State("store-auth-mode",   "data"),
    State("store-language",    "data"),
    prevent_initial_call=True,
)
def switch_auth_mode(n, mode, language):
    if not n:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    new_mode = "register" if (mode or "login") == "login" else "login"
    is_reg   = new_mode == "register"
    return (
        new_mode,
        t("register_title",  language) if is_reg else t("login_title",    language),
        t("register_btn",    language) if is_reg else t("login_btn",      language),
        t("has_account",     language) if is_reg else t("no_account",     language),
        t("login_link",      language) if is_reg else t("register_link",  language),
    )


# ============================================================
# LOGIN — soumettre
# ============================================================
@callback(
    Output("store-user",    "data", allow_duplicate=True),
    Output("url",           "pathname", allow_duplicate=True),
    Output("auth-message",  "children"),
    Input("btn-auth-submit","n_clicks"),
    State("auth-email",     "value"),
    State("auth-password",  "value"),
    State("store-auth-mode","data"),
    State("store-language", "data"),
    prevent_initial_call=True,
)
def submit_auth(n, email, password, mode, language):
    if not n: return dash.no_update, dash.no_update, dash.no_update
    if not email or not password:
        return (dash.no_update, dash.no_update,
                html.Span(t("auth_error_fields", language), className="auth-error"))
    return email, "/", ""


# ============================================================
# LANGUE — toggle + ferme settings
# ============================================================
@callback(
    Output("lang-menu",          "className"),
    Output("store-settings-open","data", allow_duplicate=True),
    Input("btn-lang",             "n_clicks"),
    State("lang-menu",            "className"),
    prevent_initial_call=True,
)
def toggle_lang_menu(n, cls):
    is_open = "visible" in cls
    return ("lang-menu hidden" if is_open else "lang-menu visible"), False


@callback(
    Output("store-language", "data"),
    Output("lang-menu",      "className", allow_duplicate=True),
    Output("btn-lang",       "children"),
    Input({"type": "btn-lang-option", "value": dash.ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def select_language(n_list):
    ctx = dash.callback_context
    if not ctx.triggered or not any(n for n in n_list if n):
        return dash.no_update, dash.no_update, dash.no_update
    lang = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["value"]
    return lang, "lang-menu hidden", LANG_CODES.get(lang, "EN")


@callback(
    Output("btn-lang", "children", allow_duplicate=True),
    Input("store-language", "data"),
    prevent_initial_call="initial_duplicate",
)
def sync_lang_btn(language):
    return LANG_CODES.get(language, "EN")


# ============================================================
# SETTINGS — toggle + ferme langue
# ============================================================
@callback(
    Output("store-settings-open", "data"),
    Output("lang-menu",           "className", allow_duplicate=True),
    Input("btn-settings",         "n_clicks"),
    State("store-settings-open",  "data"),
    prevent_initial_call=True,
)
def toggle_settings(n, is_open):
    return not bool(is_open), "lang-menu hidden"


@callback(
    Output("settings-panel", "className"),
    Input("store-settings-open", "data"),
)
def show_settings(is_open):
    return "settings-panel visible" if is_open else "settings-panel hidden"


@callback(
    Output("settings-panel", "children"),
    Input("store-language",  "data"),
    Input("store-dark-mode", "data"),
    Input("store-favorites", "data"),
    Input("store-user",      "data"),
    prevent_initial_call=True,
)
def update_settings(language, dark_mode, favorites, user):
    return settings.build_settings_panel(language, dark_mode, favorites, user)


# ============================================================
# FAVORIS — ajouter depuis le tableau top5
# ============================================================
@callback(
    Output("store-favorites", "data", allow_duplicate=True),
    Input({"type": "btn-add-fav", "index": dash.ALL}, "n_clicks"),
    State("store-favorites", "data"),
    State("store-top5-data", "data", allow_optional=True),  
    prevent_initial_call=True,
)
def add_favorite(n_clicks_list, favorites, top5_data):
    ctx = dash.callback_context

    if not ctx.triggered:
        return dash.no_update

    if not any(n_clicks_list):
        return dash.no_update

    if not top5_data:
        return dash.no_update

    idx = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["index"]

    if idx >= len(top5_data):
        return dash.no_update

    entry = top5_data[idx]

    favorites = favorites or []

    if any(f.get("nctid") == entry["nctid"] for f in favorites):
        return [f for f in favorites if f.get("nctid") != entry["nctid"]]

    return favorites + [{
        "nctid": entry["nctid"],
        "title": entry.get("interventionname", entry.get("title", ""))
    }]

# ============================================================
# THEME
# ============================================================
@callback(
    Output("app-root", "className"),
    Output("app-root", "dir"),
    Input("store-dark-mode", "data"),
    Input("store-language",  "data"),
)
def apply_theme(dark_mode, language):
    classes = ["rtl"] if is_rtl(language) else []
    return " ".join(classes), "rtl" if is_rtl(language) else "ltr"


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
