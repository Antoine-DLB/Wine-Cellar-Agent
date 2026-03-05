"""Service d'interaction avec l'API WhatsApp Business Cloud."""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


class WhatsAppService:
    """Gère l'envoi de messages et la réception de webhooks WhatsApp."""

    def __init__(self, token: str, phone_number_id: str) -> None:
        self.phone_number_id = phone_number_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def send_message(self, to: str, text: str) -> None:
        """Envoie un message texte à un numéro WhatsApp."""
        url = f"{GRAPH_API_BASE}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            logger.info("Message envoyé à %s", to)

    async def download_media(self, media_id: str) -> bytes:
        """Télécharge une image envoyée par l'utilisateur."""
        async with httpx.AsyncClient() as client:
            # Étape 1 : récupérer l'URL de téléchargement
            meta_response = await client.get(
                f"{GRAPH_API_BASE}/{media_id}",
                headers=self.headers,
                timeout=10,
            )
            meta_response.raise_for_status()
            download_url = meta_response.json()["url"]

            # Étape 2 : télécharger le fichier
            media_response = await client.get(
                download_url,
                headers=self.headers,
                timeout=30,
            )
            media_response.raise_for_status()
            logger.info("Media %s téléchargé (%d octets)", media_id, len(media_response.content))
            return media_response.content

    def parse_incoming_message(self, payload: dict) -> Optional[dict]:
        """Parse le payload webhook WhatsApp et extrait les données du message.

        Retourne un dict avec phone_number, message_type, text/media_id,
        ou None si le payload ne contient pas de message valide.
        """
        try:
            entry = payload["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]

            # Ignorer les mises à jour de statut de livraison
            if "statuses" in value:
                return None

            messages = value.get("messages")
            if not messages:
                return None

            message = messages[0]
            phone_number = message["from"]
            message_type = message["type"]

            if message_type == "text":
                return {
                    "phone_number": phone_number,
                    "message_type": "text",
                    "text": message["text"]["body"],
                    "media_id": None,
                }
            elif message_type == "image":
                return {
                    "phone_number": phone_number,
                    "message_type": "image",
                    "text": message.get("image", {}).get("caption"),
                    "media_id": message["image"]["id"],
                }
            else:
                logger.info("Type de message non supporté : %s", message_type)
                return None

        except (KeyError, IndexError) as e:
            logger.debug("Payload webhook invalide : %s", e)
            return None
