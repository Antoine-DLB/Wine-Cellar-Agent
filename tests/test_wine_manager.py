"""Tests pour WineManager."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.models.conversation import MistralIntent
from app.services.wine_manager import WineManager

MOCK_BOTTLE = {
    "id": "uuid-1",
    "name": "Château Margaux",
    "color": "rouge",
    "region": "Bordeaux",
    "appellation": "Margaux",
    "producer": "Château Margaux",
    "vintage": 2015,
    "quantity": 3,
    "drink_from": 2022,
    "drink_until": 2040,
    "purchase_price": 250.0,
}


@pytest.fixture
def manager():
    return WineManager()


@pytest.fixture
def mock_mistral():
    m = AsyncMock()
    m.get_food_pairing = AsyncMock(return_value="🥇 Château Margaux 2015 - Parfait avec l'agneau")
    return m


# ------------------------------------------------------------------ #
# add_bottle                                                           #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_add_bottle_complet(manager):
    """Ajouter une bouteille avec toutes les infos."""
    inserted = {**MOCK_BOTTLE, "created_at": "2024-01-01", "updated_at": "2024-01-01"}
    with patch("app.services.wine_manager.queries.add_bottle", new_callable=AsyncMock, return_value=inserted):
        result = await manager.add_bottle({
            "name": "Château Margaux",
            "color": "rouge",
            "region": "Bordeaux",
            "producer": "Château Margaux",
            "vintage": 2015,
            "quantity": 3,
            "drink_from": 2022,
            "drink_until": 2040,
        })
    assert "Château Margaux" in result
    assert "2015" in result
    assert "✅" in result


@pytest.mark.asyncio
async def test_add_bottle_minimal(manager):
    """Ajouter une bouteille avec seulement name et color."""
    inserted = {"id": "uuid-2", "name": "Vin de pays", "color": "blanc", "quantity": 1}
    with patch("app.services.wine_manager.queries.add_bottle", new_callable=AsyncMock, return_value=inserted):
        result = await manager.add_bottle({"name": "Vin de pays", "color": "blanc"})
    assert "Vin de pays" in result
    assert "✅" in result


# ------------------------------------------------------------------ #
# search_bottles                                                        #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_search_bottles_avec_resultats(manager):
    with patch("app.services.wine_manager.queries.search_bottles", new_callable=AsyncMock, return_value=[MOCK_BOTTLE]):
        result = await manager.search_bottles({"query": "Margaux"})
    assert "Château Margaux" in result
    assert "3 bouteille" in result  # total quantity, not reference count


@pytest.mark.asyncio
async def test_search_bottles_vide(manager):
    with patch("app.services.wine_manager.queries.search_bottles", new_callable=AsyncMock, return_value=[]):
        result = await manager.search_bottles({"query": "Inexistant"})
    assert "Aucune" in result


@pytest.mark.asyncio
async def test_search_bottles_filtre_couleur(manager):
    with patch("app.services.wine_manager.queries.search_bottles", new_callable=AsyncMock, return_value=[MOCK_BOTTLE]) as mock_search:
        await manager.search_bottles({"color": "rouge", "vintage_min": 2010})
    mock_search.assert_called_once_with(
        query=None, color="rouge", region=None,
        vintage_min=2010, vintage_max=None,
        price_min=None, price_max=None,
        sort_by=None,
    )


# ------------------------------------------------------------------ #
# remove_bottle                                                         #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_remove_bottle_quantite_superieure(manager):
    """Retirer 1 bouteille quand il en reste plusieurs."""
    decremented = {**MOCK_BOTTLE, "quantity": 2}
    with patch("app.services.wine_manager.queries.search_bottles", new_callable=AsyncMock, return_value=[MOCK_BOTTLE]):
        with patch("app.services.wine_manager.queries.decrement_quantity", new_callable=AsyncMock, return_value=decremented):
            result = await manager.remove_bottle({"search_query": "Margaux", "quantity_to_remove": 1})
    assert "2" in result
    assert "reste" in result


@pytest.mark.asyncio
async def test_remove_bottle_derniere(manager):
    """Retirer la dernière bouteille."""
    deleted = {**MOCK_BOTTLE, "quantity": 0, "deleted": True}
    with patch("app.services.wine_manager.queries.search_bottles", new_callable=AsyncMock, return_value=[MOCK_BOTTLE]):
        with patch("app.services.wine_manager.queries.decrement_quantity", new_callable=AsyncMock, return_value=deleted):
            result = await manager.remove_bottle({"search_query": "Margaux", "quantity_to_remove": 1})
    assert "dernière" in result


@pytest.mark.asyncio
async def test_remove_bottle_plusieurs_resultats(manager):
    """Plusieurs bouteilles trouvées → demande précision."""
    bottles = [MOCK_BOTTLE, {**MOCK_BOTTLE, "id": "uuid-2", "vintage": 2018}]
    with patch("app.services.wine_manager.queries.search_bottles", new_callable=AsyncMock, return_value=bottles):
        result = await manager.remove_bottle({"search_query": "Margaux"})
    assert "2 vins" in result
    assert "Précise" in result


@pytest.mark.asyncio
async def test_remove_bottle_introuvable(manager):
    with patch("app.services.wine_manager.queries.search_bottles", new_callable=AsyncMock, return_value=[]):
        result = await manager.remove_bottle({"search_query": "Inexistant"})
    assert "Aucune" in result


# ------------------------------------------------------------------ #
# maturity_check                                                        #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_maturity_check_categories(manager):
    """Vérifie la classification par catégorie de maturité."""
    current_year = date.today().year
    bottles = [
        {**MOCK_BOTTLE, "name": "Trop jeune", "drink_from": current_year + 5, "drink_until": current_year + 15},
        {**MOCK_BOTTLE, "name": "Optimal", "drink_from": current_year - 2, "drink_until": current_year + 5},
        {**MOCK_BOTTLE, "name": "A boire vite", "drink_from": current_year - 5, "drink_until": current_year + 1},
        {**MOCK_BOTTLE, "name": "Passé", "drink_from": current_year - 10, "drink_until": current_year - 2},
        {**MOCK_BOTTLE, "name": "Sans info", "drink_from": None, "drink_until": None},
    ]
    with patch("app.services.wine_manager.queries.list_all_bottles", new_callable=AsyncMock, return_value=bottles):
        result = await manager.maturity_check()
    assert "Trop jeune" in result
    assert "Optimal" in result
    assert "Passé" in result


# ------------------------------------------------------------------ #
# get_stats                                                            #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_get_stats(manager):
    stats = {
        "total_bottles": 10,
        "total_references": 5,
        "by_color": {"rouge": 6, "blanc": 4},
        "top_regions": [("Bordeaux", 6), ("Bourgogne", 4)],
        "vintage_range": (2010, 2020),
        "total_value": 500.0,
        "recent_tastings": [],
    }
    with patch("app.services.wine_manager.queries.get_stats", new_callable=AsyncMock, return_value=stats):
        result = await manager.get_stats()
    assert "10" in result
    assert "Bordeaux" in result
    assert "500" in result


# ------------------------------------------------------------------ #
# handle_intent                                                         #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_handle_intent_dispatch(manager, mock_mistral):
    """handle_intent utilise response_text de Mistral pour help."""
    intent = MistralIntent(intent="help", parameters={}, response_text="Je suis Sommelier !")
    result = await manager.handle_intent(intent, "336000", mock_mistral)
    assert result == "Je suis Sommelier !"


@pytest.mark.asyncio
async def test_handle_intent_unknown(manager, mock_mistral):
    """Intent inconnu retourne response_text de Mistral."""
    intent = MistralIntent(intent="unknown", parameters={}, response_text="Je n'ai pas compris")
    result = await manager.handle_intent(intent, "336000", mock_mistral)
    assert result == "Je n'ai pas compris"


@pytest.mark.asyncio
async def test_handle_intent_exception(manager, mock_mistral):
    """Une exception dans un handler retourne un message d'erreur propre."""
    intent = MistralIntent(intent="get_stats", parameters={}, response_text="")
    with patch("app.services.wine_manager.queries.get_stats", new_callable=AsyncMock, side_effect=Exception("DB error")):
        result = await manager.handle_intent(intent, "336000", mock_mistral)
    assert "erreur" in result.lower()
