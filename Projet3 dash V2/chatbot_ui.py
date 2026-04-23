"""
chatbot_ui.py — Interface Dash du chatbot (VERSION CORRIGÉE)
"""

from dash import html, dcc, Input, Output, State, callback
from chatbot import QUESTIONS, answer_question


def build_chatbot() -> html.Div:
    """Crée le widget flottant du chatbot"""
    return html.Div([

        # Bouton flottant
        html.Button(
            "💬",
            id="chatbot-toggle-btn",
            n_clicks=0,
            className="chatbot-toggle-btn",
        ),

        # Fenêtre du chatbot
        html.Div([

            # Header
            html.Div([
                html.H3("Clinical Trials Assistant", className="chatbot-title"),
                html.Button("✕", id="chatbot-close-btn", n_clicks=0, className="chatbot-close-btn"),
            ], className="chatbot-header"),

            # Messages
            html.Div(
                id="chatbot-messages",
                children=[
                    html.Div([
                        html.P(
                            "Bonjour 👋 Pose-moi une question sur les essais cliniques.",
                            className="chatbot-message bot"
                        )
                    ], className="chatbot-message-container"),
                ],
                className="chatbot-messages"
            ),

            # Input
            html.Div([
                dcc.Dropdown(
                    id="chatbot-question-select",
                    options=[{"label": v, "value": k} for k, v in QUESTIONS.items()],
                    placeholder="Sélectionnez une question...",
                    className="chatbot-dropdown",
                ),
                html.Button(
                    "Envoyer",
                    id="chatbot-send-btn",
                    n_clicks=0,
                    className="chatbot-send-btn"
                ),
            ], className="chatbot-input-area"),

        ], id="chatbot-window", className="chatbot-window hidden"),

    ], className="chatbot-container")


# ============================================================
# TOGGLE CHATBOT (ouvrir / fermer)
# ============================================================
@callback(
    Output("chatbot-window", "className"),
    Input("chatbot-toggle-btn", "n_clicks"),
    Input("chatbot-close-btn", "n_clicks"),
    State("chatbot-window", "className"),
    prevent_initial_call=True
)
def toggle_chatbot(n_open, n_close, current_class):

    if not current_class:
        current_class = "chatbot-window hidden"

    if "hidden" in current_class:
        return "chatbot-window"

    return "chatbot-window hidden"


# ============================================================
# ENVOI MESSAGE
# ============================================================
@callback(
    [
        Output("chatbot-messages", "children"),
        Output("chatbot-question-select", "value"),
    ],
    Input("chatbot-send-btn", "n_clicks"),
    [
        State("chatbot-question-select", "value"),
        State("chatbot-messages", "children"),
        State("store-disease", "data"),  # ✅ récupère la maladie globale
    ],
    prevent_initial_call=True,
)
def send_message(n_clicks, question_key, messages, disease):

    # sécurité
    if not question_key:
        return messages, None

    if not disease:
        disease = "unknown"

    # Question utilisateur
    question_text = QUESTIONS.get(question_key, "Question inconnue")

    new_messages = messages + [
        html.Div([
            html.P(question_text, className="chatbot-message user"),
        ], className="chatbot-message-container"),
    ]

    # Réponse bot
    answer = answer_question(question_key, disease)

    new_messages.append(
        html.Div([
            html.P(answer, className="chatbot-message bot"),
        ], className="chatbot-message-container"),
    )

    return new_messages, None