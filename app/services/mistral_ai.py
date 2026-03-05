"""Service Mistral AI pour l'analyse NLU et la vision."""

import base64
import json
import logging
from typing import Any

from mistralai import Mistral
from mistralai.models import UserMessage, SystemMessage, AssistantMessage

from app.models.conversation import MistralIntent
from app.utils.prompts import (
    SYSTEM_PROMPT_FOOD_PAIRING,
    SYSTEM_PROMPT_NLU,
    SYSTEM_PROMPT_VISION,
)

logger = logging.getLogger(__name__)

_FALLBACK_INTENT = MistralIntent(
    intent="unknown",
    parameters={},
    response_text="Désolé, je n'ai pas bien compris 😅 Peux-tu reformuler ta demande ?",
)


class MistralService:
    """Gère les appels à l'API Mistral AI."""

    def __init__(self, api_key: str) -> None:
        self.client = Mistral(api_key=api_key)

    async def analyze_message(
        self,
        user_message: str,
        conversation_history: list[dict],
    ) -> MistralIntent:
        """Analyse un message utilisateur et retourne l'intent structuré."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT_NLU}]

        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_message})

        try:
            response = await self.client.chat.complete_async(
                model="mistral-large-latest",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)
            return MistralIntent(**data)

        except json.JSONDecodeError:
            logger.warning("Réponse Mistral non parseable en JSON : %s", raw)
            return _FALLBACK_INTENT
        except Exception:
            logger.exception("Erreur lors de l'appel à Mistral NLU")
            return _FALLBACK_INTENT

    async def analyze_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> dict[str, Any]:
        """Analyse une étiquette de vin via Pixtral et extrait les informations."""
        encoded = base64.standard_b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{encoded}"

        try:
            response = await self.client.chat.complete_async(
                model="pixtral-large-latest",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": SYSTEM_PROMPT_VISION},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            raw = response.choices[0].message.content
            return json.loads(raw)

        except json.JSONDecodeError:
            logger.warning("Réponse Pixtral non parseable en JSON : %s", raw)
            return {}
        except Exception:
            logger.exception("Erreur lors de l'appel à Pixtral")
            return {}

    async def get_food_pairing(self, dish: str, bottles: list[dict]) -> str:
        """Suggère des accords mets-vin depuis la cave de l'utilisateur."""
        if not bottles:
            return "Ta cave est vide pour l'instant 😅 Ajoute quelques bouteilles et je pourrai te faire des suggestions !"

        bottles_list = "\n".join(
            f"- {b.get('name', '?')} {b.get('vintage', '') or ''} "
            f"({b.get('color', '?')}, {b.get('region') or 'région inconnue'}) "
            f"x{b.get('quantity', 1)}"
            for b in bottles
        )
        system = SYSTEM_PROMPT_FOOD_PAIRING.format(bottles_list=bottles_list)

        try:
            response = await self.client.chat.complete_async(
                model="mistral-large-latest",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Quel vin pour : {dish} ?"},
                ],
                temperature=0.5,
            )
            return response.choices[0].message.content

        except Exception:
            logger.exception("Erreur lors de l'appel food pairing Mistral")
            return "Désolé, je n'ai pas pu générer de suggestions d'accords pour le moment 🙏"
