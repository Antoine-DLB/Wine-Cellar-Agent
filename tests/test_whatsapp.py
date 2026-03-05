"""Tests pour WhatsAppService et les endpoints webhook."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.services.whatsapp import WhatsAppService


@pytest.fixture
def service():
    return WhatsAppService(token="test-token", phone_number_id="123456")


# ------------------------------------------------------------------ #
# Payloads de test                                                      #
# ------------------------------------------------------------------ #

def _text_payload(text: str = "bonjour", phone: str = "33600000000") -> dict:
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": phone,
                        "type": "text",
                        "text": {"body": text},
                    }]
                }
            }]
        }]
    }


def _image_payload(media_id: str = "media-123", caption: str | None = None) -> dict:
    msg: dict = {
        "from": "33600000000",
        "type": "image",
        "image": {"id": media_id},
    }
    if caption:
        msg["image"]["caption"] = caption
    return {
        "entry": [{"changes": [{"value": {"messages": [msg]}}]}]
    }


def _status_payload() -> dict:
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "statuses": [{"id": "msg-id", "status": "delivered"}]
                }
            }]
        }]
    }


# ------------------------------------------------------------------ #
# parse_incoming_message                                               #
# ------------------------------------------------------------------ #

def test_parse_text(service):
    result = service.parse_incoming_message(_text_payload("aide"))
    assert result is not None
    assert result["message_type"] == "text"
    assert result["text"] == "aide"
    assert result["phone_number"] == "33600000000"
    assert result["media_id"] is None


def test_parse_image(service):
    result = service.parse_incoming_message(_image_payload("media-abc"))
    assert result is not None
    assert result["message_type"] == "image"
    assert result["media_id"] == "media-abc"


def test_parse_status_retourne_none(service):
    """Un payload de statut de livraison doit retourner None."""
    result = service.parse_incoming_message(_status_payload())
    assert result is None


def test_parse_payload_vide(service):
    assert service.parse_incoming_message({}) is None


def test_parse_payload_malformed(service):
    assert service.parse_incoming_message({"entry": []}) is None


def test_parse_type_non_supporte(service):
    payload = {
        "entry": [{"changes": [{"value": {"messages": [{"from": "336", "type": "audio"}]}}]}]
    }
    assert service.parse_incoming_message(payload) is None


# ------------------------------------------------------------------ #
# Webhook GET - vérification Meta                                       #
# ------------------------------------------------------------------ #

@pytest.fixture
def client():
    """TestClient FastAPI avec l'instance settings mockée pour toute la durée du test."""
    import app.main as main_module

    mock_settings = MagicMock()
    mock_settings.whatsapp_token = "tok"
    mock_settings.whatsapp_phone_number_id = "pid"
    mock_settings.whatsapp_verify_token = "mon_token_secret"
    mock_settings.mistral_api_key = "mkey"
    mock_settings.supabase_url = "https://x.supabase.co"
    mock_settings.supabase_key = "skey"
    mock_settings.conversation_history_limit = 20

    patcher = patch.object(main_module, "settings", mock_settings)
    patcher.start()
    yield TestClient(main_module.app)
    patcher.stop()


def test_webhook_get_valide(client):
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "mon_token_secret",
            "hub.challenge": "abc123",
        },
    )
    assert response.status_code == 200
    assert response.text == "abc123"


def test_webhook_get_token_invalide(client):
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "mauvais_token",
            "hub.challenge": "abc123",
        },
    )
    assert response.status_code == 403


# ------------------------------------------------------------------ #
# Webhook POST - réception messages                                     #
# ------------------------------------------------------------------ #

def test_webhook_post_retourne_200(client):
    """Le webhook doit toujours retourner 200, même avec un payload vide."""
    response = client.post("/webhook", json={})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_post_payload_valide(client):
    """Payload valide → 200 OK (traitement en background)."""
    with patch("app.main._handle_message", new_callable=AsyncMock):
        response = client.post("/webhook", json=_text_payload("liste ma cave"))
    assert response.status_code == 200


def test_webhook_post_status_payload(client):
    """Payload de statut → 200 OK sans traitement."""
    response = client.post("/webhook", json=_status_payload())
    assert response.status_code == 200


def test_webhook_post_json_invalide(client):
    """Corps non-JSON → 200 OK (pas de crash)."""
    response = client.post(
        "/webhook",
        content=b"pas du json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200


# ------------------------------------------------------------------ #
# Health check                                                          #
# ------------------------------------------------------------------ #

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
