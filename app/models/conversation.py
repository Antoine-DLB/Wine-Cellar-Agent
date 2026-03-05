"""Modèles Pydantic pour la conversation et les intents Mistral."""

from typing import Any, Optional
from pydantic import BaseModel


class ConversationMessage(BaseModel):
    """Message de conversation WhatsApp."""

    phone_number: str
    role: str  # "user" ou "assistant"
    content: str


class MistralIntent(BaseModel):
    """Réponse structurée retournée par Mistral après analyse du message."""

    intent: str
    parameters: dict[str, Any] = {}
    response_text: str
