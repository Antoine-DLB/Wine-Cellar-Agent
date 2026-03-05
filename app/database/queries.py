"""Requêtes CRUD asynchrones pour toutes les tables Supabase."""

import logging
import re
from typing import Optional
from uuid import UUID

from app.database.supabase_client import get_supabase_client
from app.models.bottle import BottleCreate, BottleUpdate, TastingNoteCreate

logger = logging.getLogger(__name__)


# ============================================================
# Bottles
# ============================================================

async def add_bottle(bottle: BottleCreate) -> dict:
    """Insère une bouteille ou incrémente la quantité si même nom+millésime existe déjà."""
    client = get_supabase_client()

    # Chercher un doublon exact (même nom + même millésime)
    existing_query = client.table("bottles").select("*").ilike("name", bottle.name)
    if bottle.vintage:
        existing_query = existing_query.eq("vintage", bottle.vintage)
    existing = existing_query.execute().data

    if existing:
        # Incrémenter la quantité de l'entrée existante
        entry = existing[0]
        new_qty = entry["quantity"] + (bottle.quantity or 1)
        result = client.table("bottles").update({"quantity": new_qty}).eq("id", entry["id"]).execute()
        return result.data[0]

    data = bottle.model_dump(exclude_none=True)
    if "purchase_date" in data and data["purchase_date"]:
        data["purchase_date"] = str(data["purchase_date"])
    result = client.table("bottles").insert(data).execute()
    return result.data[0]


async def get_bottle_by_id(bottle_id: UUID) -> Optional[dict]:
    """Récupère une bouteille par son id."""
    client = get_supabase_client()
    result = client.table("bottles").select("*").eq("id", str(bottle_id)).execute()
    return result.data[0] if result.data else None


async def search_bottles(
    query: Optional[str] = None,
    color: Optional[str] = None,
    region: Optional[str] = None,
    vintage_min: Optional[int] = None,
    vintage_max: Optional[int] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    sort_by: Optional[str] = None,
) -> list[dict]:
    """Recherche des bouteilles avec filtres multiples.

    sort_by: "price_desc" | "price_asc" | "vintage_desc" | "vintage_asc" | None (→ tri par nom)
    """
    client = get_supabase_client()
    req = client.table("bottles").select("*")

    if color:
        req = req.eq("color", color)
    if region:
        req = req.ilike("region", f"%{region}%")
    if vintage_min:
        req = req.gte("vintage", vintage_min)
    if vintage_max:
        req = req.lte("vintage", vintage_max)
    if price_min:
        req = req.gte("purchase_price", price_min)
    if price_max:
        req = req.lte("purchase_price", price_max)
    if query:
        # Extraire une année 4 chiffres éventuelle du query (ex: "Margaux 2015" → name="Margaux", vintage=2015)
        year_match = re.search(r'\b(1[89]\d{2}|20\d{2})\b', query)
        name_query = re.sub(r'\b(1[89]\d{2}|20\d{2})\b', '', query).strip()

        if year_match and not vintage_min and not vintage_max:
            year = int(year_match.group(1))
            req = req.eq("vintage", year)

        if name_query:
            # Recherche sur le nom uniquement (ilike direct, plus fiable que or_ avec wildcards)
            req = req.ilike("name", f"%{name_query}%")

    # Tri
    match sort_by:
        case "price_desc":
            req = req.order("purchase_price", desc=True, nullsfirst=False)
        case "price_asc":
            req = req.order("purchase_price", nullsfirst=False)
        case "vintage_desc":
            req = req.order("vintage", desc=True, nullsfirst=False)
        case "vintage_asc":
            req = req.order("vintage", nullsfirst=False)
        case _:
            req = req.order("name")

    result = req.execute()
    return result.data


async def flexible_search(query: str) -> list[dict]:
    """Recherche flexible : essaie d'abord en entier, puis mot par mot si 0 résultats."""
    client = get_supabase_client()

    def _add(results: list[dict], seen: set, combined: list) -> None:
        for b in results:
            if b["id"] not in seen:
                seen.add(b["id"])
                combined.append(b)

    seen_ids: set[str] = set()
    combined: list[dict] = []

    # Tentative 1 : query complet sur le nom
    _add(await search_bottles(query=query), seen_ids, combined)
    if combined:
        return combined

    # Tentative 2 : query complet sur le producteur
    year_match = re.search(r'\b(1[89]\d{2}|20\d{2})\b', query)
    name_query = re.sub(r'\b(1[89]\d{2}|20\d{2})\b', '', query).strip()
    if name_query:
        req = client.table("bottles").select("*")
        if year_match:
            req = req.eq("vintage", int(year_match.group(1)))
        req = req.ilike("producer", f"%{name_query}%")
        _add(req.order("name").execute().data, seen_ids, combined)
    if combined:
        return combined

    # Tentative 3 : mot par mot sur nom + producteur
    words = [w for w in re.split(r'\s+', query) if len(w) > 2 and not w.isdigit()]
    for word in words:
        _add(await search_bottles(query=word), seen_ids, combined)
        req = client.table("bottles").select("*").ilike("producer", f"%{word}%")
        _add(req.order("name").execute().data, seen_ids, combined)

    return combined


async def list_all_bottles() -> list[dict]:
    """Récupère toutes les bouteilles de la cave."""
    client = get_supabase_client()
    result = client.table("bottles").select("*").order("color").order("region").order("name").execute()
    return result.data


async def update_bottle(bottle_id: UUID, updates: BottleUpdate) -> dict:
    """Met à jour une bouteille."""
    client = get_supabase_client()
    data = updates.model_dump(exclude_none=True)
    if "purchase_date" in data and data["purchase_date"]:
        data["purchase_date"] = str(data["purchase_date"])
    result = client.table("bottles").update(data).eq("id", str(bottle_id)).execute()
    return result.data[0]


async def delete_bottle(bottle_id: UUID) -> None:
    """Supprime une bouteille."""
    client = get_supabase_client()
    client.table("bottles").delete().eq("id", str(bottle_id)).execute()


async def decrement_quantity(bottle_id: UUID, quantity_to_remove: int = 1) -> dict:
    """Décrémente la quantité d'une bouteille. Supprime si quantité atteint 0."""
    bottle = await get_bottle_by_id(bottle_id)
    if not bottle:
        raise ValueError(f"Bouteille {bottle_id} introuvable")

    new_quantity = bottle["quantity"] - quantity_to_remove
    if new_quantity <= 0:
        await delete_bottle(bottle_id)
        return {**bottle, "quantity": 0, "deleted": True}

    client = get_supabase_client()
    result = client.table("bottles").update({"quantity": new_quantity}).eq("id", str(bottle_id)).execute()
    return result.data[0]


# ============================================================
# Tasting log
# ============================================================

async def add_tasting_note(note: TastingNoteCreate) -> dict:
    """Enregistre une note de dégustation."""
    client = get_supabase_client()
    data = note.model_dump(exclude_none=True)
    if "bottle_id" in data and data["bottle_id"]:
        data["bottle_id"] = str(data["bottle_id"])
    if "tasted_at" in data:
        data["tasted_at"] = str(data["tasted_at"])
    result = client.table("tasting_log").insert(data).execute()
    return result.data[0]


async def list_tasting_notes(
    limit: int = 10,
    min_rating: Optional[int] = None,
) -> list[dict]:
    """Récupère l'historique des dégustations."""
    client = get_supabase_client()
    req = client.table("tasting_log").select("*")
    if min_rating:
        req = req.gte("rating", min_rating)
    result = req.order("tasted_at", desc=True).limit(limit).execute()
    return result.data


# ============================================================
# Conversation history
# ============================================================

async def add_message(phone_number: str, role: str, content: str) -> dict:
    """Ajoute un message à l'historique de conversation."""
    client = get_supabase_client()
    result = client.table("conversation_history").insert({
        "phone_number": phone_number,
        "role": role,
        "content": content,
    }).execute()
    return result.data[0]


async def get_recent_messages(phone_number: str, limit: int = 20) -> list[dict]:
    """Récupère les N derniers messages d'un numéro (ordre chronologique)."""
    client = get_supabase_client()
    result = (
        client.table("conversation_history")
        .select("role, content")
        .eq("phone_number", phone_number)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    # Inverser pour avoir l'ordre chronologique (plus ancien en premier)
    return list(reversed(result.data))


# ============================================================
# Stats
# ============================================================

async def get_stats() -> dict:
    """Retourne les statistiques agrégées de la cave."""
    client = get_supabase_client()

    bottles = client.table("bottles").select("*").execute().data
    tasting = client.table("tasting_log").select("*").order("tasted_at", desc=True).limit(5).execute().data

    total_bottles = sum(b.get("quantity", 1) for b in bottles)
    total_references = len(bottles)

    # Répartition par couleur
    by_color: dict[str, int] = {}
    for b in bottles:
        color = b.get("color", "inconnu")
        by_color[color] = by_color.get(color, 0) + b.get("quantity", 1)

    # Répartition par région (top 5)
    by_region: dict[str, int] = {}
    for b in bottles:
        region = b.get("region") or "Non renseigné"
        by_region[region] = by_region.get(region, 0) + b.get("quantity", 1)
    top_regions = sorted(by_region.items(), key=lambda x: x[1], reverse=True)[:5]

    # Millésimes
    vintages = [b["vintage"] for b in bottles if b.get("vintage")]
    vintage_range = (min(vintages), max(vintages)) if vintages else None

    # Valeur totale
    total_value = sum(
        (b.get("purchase_price") or 0) * b.get("quantity", 1)
        for b in bottles
    )

    return {
        "total_bottles": total_bottles,
        "total_references": total_references,
        "by_color": by_color,
        "top_regions": top_regions,
        "vintage_range": vintage_range,
        "total_value": total_value,
        "recent_tastings": tasting,
    }
