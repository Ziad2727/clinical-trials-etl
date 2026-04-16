"""
pages/disease.py — Page par maladie
"""

import plotly.graph_objects as go
import pandas as pd
from dash import html, dcc, callback, Input, Output, State
from translations import t
from data import (
    disease_active_count, disease_phase_dist,
    disease_trials_per_year, disease_geo, top5_for_disease,
    get_disease_list,
)

TEAL   = "#3ad8a9"
AMBER  = "#f5a623"
PURPLE = "#9b82f3"
BLUE   = "#74b9f7"
MUTED  = "#4b6b5f"
FAINT  = "#94b4a8"
BORDER = "rgba(58,216,169,0.2)"

PHASE_COLORS = {
    "Phase I": BLUE, "Phase II": TEAL,
    "Phase III": AMBER, "Phase IV": PURPLE,
}
PHASE_ORDER = ["Phase I", "Phase II", "Phase III", "Phase IV"]

BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(0,0,0,0)",
    font=dict(family="IBM Plex Mono, monospace", color=MUTED, size=11),
)


def build_disease_page(disease: str, language: str = "English",
                       dis_options: list = None) -> html.Div:
    name         = disease.replace("_", " ")
    active_count = disease_active_count(disease)
    phases       = disease_phase_dist(disease)
    by_year      = disease_trials_per_year(disease)
    geo          = disease_geo(disease)
    top5         = top5_for_disease(disease)
    options      = dis_options or [{"label": d, "value": d} for d in get_disease_list()]

    return html.Div([

        # ── Sélecteur en haut ─────────────────────────────────
        html.Div([
            html.P(t("explore_label", language), className="explore-label"),
            html.Div([
                dcc.Dropdown(
                    id="disease-page-selector",
                    options=options,
                    value=disease,
                    placeholder=t("select_disease", language),
                    clearable=False,
                    className="welcome-disease-dropdown",
                    style={"color": "#111827"},
                ),
                html.Button(
                    t("explore_btn", language),
                    id="btn-disease-explore",
                    n_clicks=0,
                    className="cta-btn explore-btn",
                ),
            ], className="explore-row"),
        ], className="explore-section", style={"marginTop": "1.5rem"}),

        html.Hr(className="ct-divider"),

        # ── Header ────────────────────────────────────────────
        html.Div([
            html.P(t("welcome_eyebrow", language), className="hero-eyebrow",
                   style={"textAlign": "left", "marginBottom": "0.3rem"}),
            html.H2(name, className="browse-title"),
            html.P(f"{t('disease_active', language)} : {active_count:,}",
                   className="browse-subtitle"),
        ], className="browse-header"),

        html.Div([
            _chip(f"{active_count:,}", t("disease_active", language)),
        ], className="stat-bar", style={"marginBottom": "2rem"}),

        html.Hr(className="ct-divider"),

        _section(
            t("top5_title", language), t("top5_desc", language),
            _top5_chart(top5) if not top5.empty
            else html.P(t("no_results", language),
                        style={"color": MUTED, "fontFamily": "IBM Plex Mono", "padding": "1rem 0"}),
        ),
        _top5_table(top5, language) if not top5.empty else html.Div(),

        html.Hr(className="ct-divider"),

        _section(t("disease_phase_title", language), t("disease_phase_desc", language),
            dcc.Graph(figure=_phase_bar(phases), config={"displayModeBar": False}, className="kpi-chart")),

        _section(t("disease_time_title", language), t("disease_time_desc", language),
            dcc.Graph(figure=_line_chart(by_year), config={"displayModeBar": False}, className="kpi-chart")),

        _section(t("disease_geo_title", language), t("disease_geo_desc", language),
            dcc.Graph(figure=_world_map(geo), config={"displayModeBar": False}, className="kpi-chart kpi-chart--map")),

        html.Div(t("footer", language), className="ct-footer"),

    ], className="browse-page")


def _top5_chart(top: pd.DataFrame) -> dcc.Graph:
    top = top.copy().sort_values("score", ascending=True)
    top["label"] = top["interventionname"].apply(lambda s: (s[:44] + "…") if len(s) > 44 else s)

    def pl(p):
        if "PHASE4" in p: return "Phase IV"
        if "PHASE3" in p: return "Phase III"
        if "PHASE2" in p: return "Phase II"
        return "Phase I"

    top["phase_label"] = top["phase"].apply(pl)
    enr = top["enrollment"].values.astype(float)
    emin, emax = enr.min(), enr.max()
    sizes = (12 + 28 * (enr - emin) / (emax - emin)).tolist() if emax > emin else [22] * len(top)

    fig = go.Figure()
    for phase_name in PHASE_ORDER:
        sub = top[top["phase_label"] == phase_name]
        if sub.empty: continue
        sub_idx = [list(top.index).index(i) for i in sub.index]
        fig.add_trace(go.Scatter(
            x=sub["phase_label"].tolist(), y=sub["label"].tolist(), mode="markers", name=phase_name,
            marker=dict(
                color=sub["score"].tolist(),
                colorscale=[[0, "#1aaf84"], [0.5, TEAL], [1, "#a8f5df"]],
                cmin=0, cmax=100, size=[sizes[i] for i in sub_idx],
                line=dict(width=1, color="rgba(58,216,169,0.35)"), showscale=True,
                colorbar=dict(title=dict(text="Score", font=dict(color=MUTED, size=10)),
                              thickness=10, len=0.6, tickfont=dict(color=MUTED, size=9)),
            ),
            customdata=sub[["nctid", "enrollment", "score", "sponsortype", "region"]].values,
            hovertemplate="<b>%{y}</b><br>Phase : %{x}<br>NCT ID : %{customdata[0]}<br>Enrollment : %{customdata[1]:,.0f}<br>Score : %{customdata[2]:.0f}<br>Sponsor : %{customdata[3]}<br>Region : %{customdata[4]}<br><extra></extra>",
        ))

    fig.update_layout(**{**BASE,
        "height": max(300, len(top) * 65), "showlegend": True,
        "xaxis": dict(title="Clinical Phase", categoryorder="array", categoryarray=PHASE_ORDER,
                      gridcolor=BORDER, tickfont=dict(size=11, color=MUTED)),
        "yaxis": dict(gridcolor=BORDER, tickfont=dict(size=10, color=MUTED), automargin=True),
        "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color=MUTED, size=10)),
        "margin": dict(l=16, r=90, t=55, b=16),
    })
    return dcc.Graph(figure=fig, config={"displayModeBar": False}, className="kpi-chart top5-chart")


def _top5_table(top: pd.DataFrame, language: str) -> html.Div:
    sorted_top = top.sort_values("score", ascending=False)
    # Stocker nctid+title dans un Store pour que le callback puisse y accéder
    fav_data = [
        {"nctid": row["nctid"], "title": row["interventionname"]}
        for _, row in sorted_top.iterrows()
    ]
    rows = []
    for i, (_, row) in enumerate(sorted_top.iterrows()):
        p = row["phase"]
        badge = "phase-badge p4" if "PHASE4" in p else "phase-badge p3" if "PHASE3" in p else "phase-badge p2" if "PHASE2" in p else "phase-badge nct"
        nctid = row["nctid"]
        title = row["interventionname"]
        rows.append(html.Tr([
            html.Td(html.Div([
                html.A(nctid, href=f"https://clinicaltrials.gov/study/{nctid}",
                       target="_blank", className="nct-link"),
                html.Button(
                    "♡",
                    id={"type": "btn-add-fav", "index": i},
                    n_clicks=0,
                    className="fav-btn",
                ),
            ], className="nct-cell")),
            html.Td(title, className="td-intervention"),
            html.Td(html.Span(p.replace("PHASE", "Phase "), className=badge)),
            html.Td(f"{int(row['enrollment']):,}"),
            html.Td(row["region"]),
            html.Td(html.Span(f"{row['score']:.0f}", className="score-badge")),
        ]))
    table = html.Table([
        html.Thead(html.Tr([html.Th("NCT ID"), html.Th(t("intervention", language)),
                            html.Th(t("phase", language)), html.Th(t("participants", language)),
                            html.Th(t("region", language)), html.Th(t("score", language))])),
        html.Tbody(rows),
    ], className="top5-data-table", style={"marginBottom": "2rem"})
    return html.Div([
        dcc.Store(id="store-top5-data", data=fav_data),
        table,
    ])


def _phase_bar(df):
    colors = [PHASE_COLORS.get(str(p), FAINT) for p in df["Phase"]]
    fig = go.Figure(go.Bar(x=df["Phase"].astype(str), y=df["Count"],
                           marker=dict(color=colors, opacity=0.9),
                           hovertemplate="%{x}: %{y:,}<extra></extra>"))
    fig.update_layout(**{**BASE, "height": 260, "xaxis": dict(gridcolor=BORDER),
                         "yaxis": dict(gridcolor=BORDER), "margin": dict(l=16, r=16, t=40, b=16)})
    return fig


def _line_chart(df):
    fig = go.Figure(go.Scatter(x=df["startyear"], y=df["Count"], mode="lines+markers",
                               line=dict(color=TEAL, width=2), marker=dict(color=TEAL, size=6),
                               fill="tozeroy", fillcolor="rgba(58,216,169,0.07)",
                               hovertemplate="%{x}: %{y:,}<extra></extra>"))
    fig.update_layout(**{**BASE, "height": 260, "xaxis": dict(gridcolor=BORDER, dtick=2),
                         "yaxis": dict(gridcolor=BORDER), "margin": dict(l=16, r=16, t=40, b=16)})
    return fig


def _world_map(geo):
    fig = go.Figure(go.Choropleth(
        locations=geo["Country"], locationmode="country names", z=geo["Count"],
        colorscale=[[0, "#edfaf4"], [0.3, "#3ad8a9"], [1, "#1aaf84"]],
        marker=dict(line=dict(color="rgba(58,216,169,0.3)", width=0.5)),
        colorbar=dict(title=dict(text="Trials", font=dict(color=MUTED, size=10)),
                      thickness=10, len=0.6, tickfont=dict(color=MUTED, size=9), bgcolor="rgba(0,0,0,0)"),
        hovertemplate="%{location}: %{z:,} trials<extra></extra>",
    ))
    fig.update_layout(**{**BASE, "height": 380,
        "geo": dict(showframe=False, showcoastlines=True, coastlinecolor="rgba(58,216,169,0.3)",
                    showland=True, landcolor="#f5fdf9", showocean=True, oceancolor="#e8f8ff",
                    showcountries=True, countrycolor="rgba(58,216,169,0.2)",
                    bgcolor="rgba(0,0,0,0)", projection_type="natural earth"),
        "margin": dict(l=0, r=0, t=10, b=0),
    })
    return fig


def _chip(value, label):
    return html.Div([html.Div(value, className="stat-value"),
                     html.Div(label, className="stat-label")], className="stat-item")


def _section(title, desc, content):
    return html.Div([
        html.Div([html.H3(title, className="section-title"),
                  html.P(desc, className="section-desc")], className="section-header"),
        content,
    ], className="browse-section")
