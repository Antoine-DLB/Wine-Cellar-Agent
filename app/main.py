"""Point d'entrée FastAPI - Webhook WhatsApp."""

import logging
import re

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.config import Settings
from app.database.queries import add_message, get_recent_messages
from app.models.conversation import MistralIntent
from app.services.image_analyzer import ImageAnalyzer
from app.services.mistral_ai import MistralService
from app.services.whatsapp import WhatsAppService
from app.services.wine_manager import WineManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = Settings()

app = FastAPI(title="Wine Cellar Bot")

whatsapp = WhatsAppService(
    token=settings.whatsapp_token,
    phone_number_id=settings.whatsapp_phone_number_id,
)
mistral = MistralService(api_key=settings.mistral_api_key)
wine_manager = WineManager()
image_analyzer = ImageAnalyzer()


# ============================================================
# Health check
# ============================================================

@app.get("/health")
async def health() -> dict:
    """Vérifie que le serveur est opérationnel."""
    return {"status": "ok"}


# ============================================================
# Webhook WhatsApp - vérification Meta
# ============================================================

@app.get("/webhook")
async def verify_webhook(request: Request) -> PlainTextResponse:
    """Endpoint de vérification du webhook par Meta."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("Webhook vérifié avec succès")
        return PlainTextResponse(content=challenge)

    logger.warning("Échec de vérification du webhook (token invalide)")
    raise HTTPException(status_code=403, detail="Token de vérification invalide")


# ============================================================
# Traitement des messages (arrière-plan)
# ============================================================

async def process_text_message(phone_number: str, text: str) -> None:
    """Traite un message texte : NLU → action → réponse → historique."""
    logger.info("Traitement message texte de %s", phone_number)

    # 1. Charger l'historique de conversation
    history = await get_recent_messages(phone_number, limit=settings.conversation_history_limit)

    # 2. Analyser l'intent via Mistral
    intent: MistralIntent = await mistral.analyze_message(text, history)
    logger.info("Intent détecté : %s", intent.intent)

    # 3. Exécuter l'action métier
    response_text = await wine_manager.handle_intent(intent, phone_number, mistral)

    # 4. Envoyer la réponse WhatsApp (sans la ligne [CANDIDATS:] — contexte machine uniquement)
    whatsapp_text = re.sub(r'\n\[(CANDIDATS|BOUTEILLE_SUPPRIMEE):[^\n]*\]', '', response_text).strip()
    await whatsapp.send_message(phone_number, whatsapp_text)

    # 5. Sauvegarder les deux messages dans l'historique (full response avec [CANDIDATS] pour Mistral)
    await add_message(phone_number, "user", text)
    await add_message(phone_number, "assistant", response_text)

    logger.info("Réponse envoyée à %s", phone_number)


async def process_image_message(phone_number: str, media_id: str, caption: str | None) -> None:
    """Traite un message image : téléchargement → analyse étiquette → confirmation."""
    logger.info("Traitement image de %s (media_id=%s)", phone_number, media_id)

    # 1. Télécharger l'image
    image_bytes = await whatsapp.download_media(media_id)

    # 2. Analyser via ImageAnalyzer (valide + formate)
    response_text, wine_data = await image_analyzer.analyze_and_format(
        image_bytes=image_bytes,
        mime_type="image/jpeg",
        mistral_service=mistral,
    )

    # 3. Envoyer le résultat
    await whatsapp.send_message(phone_number, response_text)

    # 4. Sauvegarder dans l'historique (user d'abord, puis assistant)
    await add_message(phone_number, "user", caption or "[Photo d'étiquette envoyée]")

    # Préfixe machine-readable pour que Mistral sache exactement quelle bouteille est en attente
    if wine_data:
        assistant_msg = (
            f"[BOUTEILLE_EN_ATTENTE: name={wine_data.get('name')!r}, "
            f"vintage={wine_data.get('vintage')}, color={wine_data.get('color')!r}, "
            f"region={wine_data.get('region')!r}, appellation={wine_data.get('appellation')!r}, "
            f"producer={wine_data.get('producer')!r}, "
            f"grape_varieties={wine_data.get('grape_varieties')}]\n{response_text}"
        )
    else:
        assistant_msg = response_text
    await add_message(phone_number, "assistant", assistant_msg)

    logger.info("Analyse image envoyée à %s", phone_number)


async def _handle_message(parsed: dict) -> None:
    """Dispatch vers le bon handler selon le type de message."""
    phone_number = parsed["phone_number"]
    try:
        if parsed["message_type"] == "text":
            await process_text_message(phone_number, parsed["text"])
        elif parsed["message_type"] == "image":
            await process_image_message(phone_number, parsed["media_id"], parsed.get("text"))
    except Exception:
        logger.exception("Erreur non gérée pour le message de %s", phone_number)
        try:
            await whatsapp.send_message(
                phone_number,
                "Une erreur inattendue s'est produite 😓 Réessaie dans un instant.",
            )
        except Exception:
            logger.exception("Impossible d'envoyer le message d'erreur à %s", phone_number)


# ============================================================
# Webhook WhatsApp - réception des messages
# ============================================================

@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    """Réception et traitement des messages WhatsApp entrants."""
    try:
        payload = await request.json()
    except Exception:
        logger.warning("Payload webhook non parseable")
        return {"status": "ok"}

    parsed = whatsapp.parse_incoming_message(payload)
    if parsed:
        background_tasks.add_task(_handle_message, parsed)
    else:
        logger.debug("Payload ignoré (statut ou type non supporté)")

    # Toujours retourner 200 rapidement pour Meta
    return {"status": "ok"}
