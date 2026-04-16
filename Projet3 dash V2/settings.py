from dash import html, dcc, Input, Output, State, callback, ALL
import dash
import json
from translations import t


def build_settings_panel(language, dark_mode, favorites, user=None):
    is_logged = user is not None
    return html.Div([
        html.H2(t("settings_title", language), className="settings-title"),
        html.Hr(className="ct-divider"),

        # ── Favoris ───────────────────────────────────────────
        html.Div([
            html.H4(t("favorites", language), className="settings-subtitle"),
            _render_favorites(favorites, language),
        ], className="settings-section"),

        html.Hr(className="ct-divider"),

        # ── Compte ────────────────────────────────────────────
        html.Div([
            html.H4(t("account", language), className="settings-subtitle"),
            html.Div(id="auth-panel-content", children=_auth_content(is_logged, user, language)),
        ], className="settings-section"),

    ], className="settings-inner")


def _auth_content(is_logged, user, language):
    if is_logged:
        return html.Div([
            html.P(f"{t('logged_as', language)} {user}", className="logged-as-text"),
            html.Button(t("logout_btn", language), id="btn-logout",
                        n_clicks=0, className="logout-btn"),
            html.Div(id="logout-confirm-msg"),
        ])
    else:
        return html.Div([
            html.Button(t("login_btn", language), id="btn-show-login",
                        n_clicks=0, className="login-btn"),
            html.Div(id="logout-confirm-msg"),
        ])


def _render_favorites(favorites, language):
    if not favorites:
        return html.P(t("no_favorites", language), className="no-favorites")
    return html.Div([
        html.Div([
            html.Div([
                html.Strong(s.get("nctid", "N/A")),
                html.Br(),
                html.Span(s.get("title", "N/A")),
            ], className="favorite-card", style={"flex": "4"}),
            html.Button(t("remove", language),
                        id={"type": "btn-remove-fav", "index": i},
                        n_clicks=0, className="remove-btn"),
        ], className="favorite-row")
        for i, s in enumerate(favorites)
    ])


# ── Callbacks ────────────────────────────────────────────────

@callback(
    Output("store-favorites", "data"),
    Input({"type": "btn-remove-fav", "index": ALL}, "n_clicks"),
    State("store-favorites", "data"),
    prevent_initial_call=True,
)
def remove_favorite(n_clicks_list, favorites):
    ctx = dash.callback_context
    if not ctx.triggered or not any(n_clicks_list):
        return favorites
    idx = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["index"]
    return [f for i, f in enumerate(favorites) if i != idx]


@callback(
    Output("store-user",          "data", allow_duplicate=True),
    Output("store-favorites",     "data", allow_duplicate=True),
    Output("store-settings-open", "data", allow_duplicate=True),
    Output("logout-confirm-msg",  "children"),
    Input("btn-logout", "n_clicks"),
    State("store-language", "data"),
    prevent_initial_call=True,
)
def logout(n_clicks, language):
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    return None, [], False, html.Div(t("logout_confirm", language), className="logout-confirm")


@callback(
    Output("url",                 "pathname", allow_duplicate=True),
    Output("store-settings-open", "data",     allow_duplicate=True),
    Input("btn-show-login", "n_clicks"),
    prevent_initial_call=True,
)
def go_to_login(n):
    if not n:
        return dash.no_update, dash.no_update
    return "/login", False
