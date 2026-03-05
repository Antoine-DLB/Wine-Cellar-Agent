"""Tests pour MistralService."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.conversation import MistralIntent
from app.services.mistral_ai import MistralService


@pytest.fixture
def service():
    return MistralService(api_key="test-key")


def _mock_response(content: str):
    """Construit un faux objet de réponse Mistral."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


# ------------------------------------------------------------------ #
# analyze_message                                                       #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_analyze_message_valide(service):
    """Parsing JSON valide → MistralIntent correct."""
    payload = json.dumps({
        "intent": "add_bottle",
        "parameters": {"name": "Pomerol", "color": "rouge"},
        "response_text": "J'ajoute le Pomerol !",
    })
    with patch.object(service.client.chat, "complete_async", new_callable=AsyncMock, return_value=_mock_response(payload)):
        result = await service.analyze_message("ajoute un Pomerol rouge", [])
    assert result.intent == "add_bottle"
    assert result.parameters["name"] == "Pomerol"
    assert "Pomerol" in result.response_text


@pytest.mark.asyncio
async def test_analyze_message_json_invalide(service):
    """Réponse non-JSON → fallback intent 'unknown'."""
    with patch.object(service.client.chat, "complete_async", new_callable=AsyncMock, return_value=_mock_response("pas du JSON")):
        result = await service.analyze_message("test", [])
    assert result.intent == "unknown"
    assert result.response_text  # message d'excuse non vide


@pytest.mark.asyncio
async def test_analyze_message_exception_api(service):
    """Exception API → fallback intent 'unknown'."""
    with patch.object(service.client.chat, "complete_async", new_callable=AsyncMock, side_effect=Exception("timeout")):
        result = await service.analyze_message("test", [])
    assert result.intent == "unknown"


@pytest.mark.asyncio
async def test_analyze_message_avec_historique(service):
    """L'historique de conversation est transmis correctement."""
    payload = json.dumps({"intent": "list_all", "parameters": {}, "response_text": "Voici ta cave"})
    history = [
        {"role": "user", "content": "bonjour"},
        {"role": "assistant", "content": "Bonjour ! Comment puis-je t'aider ?"},
    ]
    captured_messages = []

    async def fake_complete(**kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        return _mock_response(payload)

    with patch.object(service.client.chat, "complete_async", side_effect=fake_complete):
        await service.analyze_message("liste ma cave", history)

    roles = [m["role"] for m in captured_messages]
    assert "system" in roles
    assert roles.count("user") >= 2  # historique + message courant


@pytest.mark.asyncio
async def test_analyze_message_json_partiel(service):
    """JSON valide mais champs manquants → fallback."""
    with patch.object(service.client.chat, "complete_async", new_callable=AsyncMock, return_value=_mock_response('{"intent": "help"}')):
        result = await service.analyze_message("aide", [])
    # Pydantic lève une erreur si response_text manque → fallback
    assert result.intent == "unknown"


# ------------------------------------------------------------------ #
# analyze_image                                                         #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_analyze_image_valide(service):
    """Analyse d'image réussie → dict avec infos du vin."""
    wine_data = {
        "name": "Château Pétrus",
        "producer": "Pétrus",
        "region": "Pomerol",
        "vintage": 2018,
        "color": "rouge",
        "confidence": 0.92,
    }
    with patch.object(service.client.chat, "complete_async", new_callable=AsyncMock, return_value=_mock_response(json.dumps(wine_data))):
        result = await service.analyze_image(b"fake-image-bytes", "image/jpeg")
    assert result["name"] == "Château Pétrus"
    assert result["vintage"] == 2018
    assert result["confidence"] == 0.92


@pytest.mark.asyncio
async def test_analyze_image_json_invalide(service):
    """Réponse non-JSON pour une image → dict vide."""
    with patch.object(service.client.chat, "complete_async", new_callable=AsyncMock, return_value=_mock_response("impossible à lire")):
        result = await service.analyze_image(b"bad-image")
    assert result == {}


@pytest.mark.asyncio
async def test_analyze_image_exception(service):
    """Exception API pour une image → dict vide."""
    with patch.object(service.client.chat, "complete_async", new_callable=AsyncMock, side_effect=Exception("network")):
        result = await service.analyze_image(b"bytes")
    assert result == {}


# ------------------------------------------------------------------ #
# get_food_pairing                                                      #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_get_food_pairing_avec_bouteilles(service):
    bottles = [{"name": "Château Margaux", "vintage": 2015, "color": "rouge", "region": "Bordeaux", "quantity": 2}]
    with patch.object(service.client.chat, "complete_async", new_callable=AsyncMock, return_value=_mock_response("🥇 Château Margaux 2015 - Idéal avec l'agneau")):
        result = await service.get_food_pairing("gigot d'agneau", bottles)
    assert "Château Margaux" in result


@pytest.mark.asyncio
async def test_get_food_pairing_cave_vide(service):
    """Cave vide → message d'information sans appel API."""
    result = await service.get_food_pairing("saumon", [])
    assert "vide" in result.lower()


@pytest.mark.asyncio
async def test_get_food_pairing_exception(service):
    bottles = [{"name": "Test", "vintage": 2020, "color": "blanc", "region": None, "quantity": 1}]
    with patch.object(service.client.chat, "complete_async", new_callable=AsyncMock, side_effect=Exception("timeout")):
        result = await service.get_food_pairing("poisson", bottles)
    assert "Désolé" in result
