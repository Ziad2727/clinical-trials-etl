"""
pages/favorites.py — Page des études favorites
"""

from dash import html, dcc, Input, Output, State, callback, ALL
import dash
import json
from translations import t


def build_favorites_page(language: str = "English") -> html.Div:
    return html.Div([
        html.Div([
            html.P(t("welcome_eyebrow", language), className="hero-eyebrow",
                   style={"textAlign": "left", "marginBottom": "0.3rem"}),
            html.H2(t("favorites", language), className="browse-title"),
            html.P(t("favorites_desc", language) if "favorites_desc" in _KEYS else
                   "Your saved clinical trials", className="browse-subtitle"),
        ], className="browse-header"),

        html.Hr(className="ct-divider"),

        html.Div(id="favorites-list-content"),

        html.Div(t("footer", language), className="ct-footer"),
    ], className="browse-page")


_KEYS = []  # placeholder


@callback(
    Output("favorites-list-content", "children"),
    Input("store-favorites", "data"),
    Input("store-language",  "data"),
)
def render_favorites(favorites, language):
    if not favorites:
        return html.Div([
            html.P("♡", style={"fontSize": "3rem", "textAlign": "center",
                                "color": "#3ad8a9", "marginTop": "3rem"}),
            html.P(t("no_favorites", language),
                   style={"textAlign": "center", "color": "#4b6b5f",
                          "fontFamily": "IBM Plex Mono", "fontSize": "0.9rem"}),
        ])

    rows = []
    for i, fav in enumerate(favorites):
        nctid = fav.get("nctid", "N/A")
        title = fav.get("title", "N/A")
        rows.append(html.Tr([
            html.Td(
                html.A(nctid,
                       href=f"https://clinicaltrials.gov/study/{nctid}",
                       target="_blank", className="nct-link"),
            ),
            html.Td(title, className="td-intervention"),
            html.Td(
                html.Button("✕", id={"type": "btn-remove-fav-page", "index": i},
                            n_clicks=0, className="remove-btn"),
            ),
        ]))

    return html.Table([
        html.Thead(html.Tr([
            html.Th("NCT ID"),
            html.Th(t("intervention", language)),
            html.Th(""),
        ])),
        html.Tbody(rows),
    ], className="top5-data-table")


@callback(
    Output("store-favorites", "data", allow_duplicate=True),
    Input({"type": "btn-remove-fav-page", "index": ALL}, "n_clicks"),
    State("store-favorites", "data"),
    prevent_initial_call=True,
)
def remove_fav_from_page(n_clicks_list, favorites):
    ctx = dash.callback_context
    if not ctx.triggered or not any(n_clicks_list):
        return dash.no_update
    idx = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["index"]
    return [f for i, f in enumerate(favorites) if i != idx]
