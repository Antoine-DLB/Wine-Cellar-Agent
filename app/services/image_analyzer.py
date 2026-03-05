"""Analyse d'étiquettes de vin via Pixtral et formatage pour confirmation."""

import logging
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.mistral_ai import MistralService

logger = logging.getLogger(__name__)

VALID_COLORS = {"rouge", "blanc", "rosé", "champagne", "mousseux", "liquoreux"}
CURRENT_YEAR = date.today().year


def _validate(data: dict) -> dict:
    """Nettoie et valide les données extraites de l'étiquette."""
    cleaned = dict(data)

    # Vintage : doit être un entier entre 1900 et l'année courante
    vintage = cleaned.get("vintage")
    if vintage is not None:
        try:
            vintage = int(vintage)
            if not (1900 <= vintage <= CURRENT_YEAR):
                vintage = None
        except (ValueError, TypeError):
            vintage = None
    cleaned["vintage"] = vintage

    # Couleur : doit être dans la liste autorisée
    color = cleaned.get("color")
    if color and color.lower() not in VALID_COLORS:
        cleaned["color"] = None
    elif color:
        cleaned["color"] = color.lower()

    # Confidence : entre 0.0 et 1.0
    confidence = cleaned.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
            cleaned["confidence"] = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            cleaned["confidence"] = None

    # Grape varieties : doit être une liste
    grape_varieties = cleaned.get("grape_varieties")
    if grape_varieties and not isinstance(grape_varieties, list):
        cleaned["grape_varieties"] = [str(grape_varieties)]

    return cleaned


def _format_confirmation(data: dict) -> str:
    """Formate le message de confirmation pour l'utilisateur WhatsApp."""
    lines = ["📸 *J'ai analysé l'étiquette !* Voici ce que j'ai trouvé :\n"]

    name = data.get("name") or "Vin non identifié"
    vintage = data.get("vintage")
    vintage_str = f" {vintage}" if vintage else ""
    lines.append(f"🍷 *{name}{vintage_str}*")

    if data.get("producer"):
        lines.append(f"🏰 {data['producer']}")

    location_parts = list(filter(None, [data.get("appellation"), data.get("region")]))
    if location_parts:
        lines.append(f"📍 {', '.join(location_parts)}")

    if data.get("grape_varieties"):
        lines.append(f"🍇 {', '.join(data['grape_varieties'])}")

    if data.get("color"):
        lines.append(f"🎨 {data['color'].capitalize()}")

    confidence = data.get("confidence")
    if confidence is not None:
        stars = round(confidence * 5)
        lines.append(
            f"\nConfiance : {'⭐' * stars}{'☆' * (5 - stars)} ({int(confidence * 100)}%)"
        )

    lines.append(
        "\nTu veux que j'ajoute cette bouteille à ta cave ? "
        "Dis-moi aussi :\n"
        "💶 Prix d'achat (ex: 25€)\n"
        "📦 Quantité (défaut : 1)\n"
        "📍 Emplacement (ex: Cave principale, Frigo à vin…)\n\n"
        "_Tu peux corriger les infos ci-dessus si besoin, ou confirmer directement si tu n'as pas ces détails 😊_"
    )
    return "\n".join(lines)


class ImageAnalyzer:
    """Orchestre l'analyse d'étiquettes de vin via Pixtral."""

    async def analyze_and_format(
        self,
        image_bytes: bytes,
        mime_type: str,
        mistral_service: "MistralService",
    ) -> tuple[str, dict]:
        """Analyse l'image, valide les données.

        Retourne (message_confirmation, wine_data).
        wine_data est vide si l'analyse a échoué.
        """
        # 1. Analyser l'étiquette via Pixtral
        raw_data = await mistral_service.analyze_image(image_bytes, mime_type)

        if not raw_data:
            return (
                "Je n'ai pas réussi à lire cette étiquette 😕\n"
                "Essaie avec une photo plus nette, bien éclairée et de face.",
                {},
            )

        # 2. Valider et nettoyer les données
        data = _validate(raw_data)
        logger.info(
            "Étiquette analysée : %s %s (confiance=%.0f%%)",
            data.get("name", "?"),
            data.get("vintage", ""),
            (data.get("confidence") or 0) * 100,
        )

        # 3. Formater le message de confirmation
        confirmation_msg = _format_confirmation(data)

        return confirmation_msg, data
