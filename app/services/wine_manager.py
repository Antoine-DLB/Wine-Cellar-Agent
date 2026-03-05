"""Logique métier - orchestre les actions selon les intents Mistral."""

import logging
import re
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from app.database import queries
from app.database.queries import flexible_search
from app.models.bottle import (
    BottleCreate,
    TastingNoteCreate,
)
from app.models.conversation import MistralIntent

if TYPE_CHECKING:
    from app.services.mistral_ai import MistralService

logger = logging.getLogger(__name__)

COLOR_EMOJI = {
    "rouge": "🔴",
    "blanc": "⚪",
    "rosé": "🌸",
    "champagne": "🥂",
    "mousseux": "🫧",
    "liquoreux": "🍯",
}

MAX_MSG_LENGTH = 4096


def _stars(rating: int) -> str:
    return "⭐" * rating + "☆" * (5 - rating)


def _truncate(text: str) -> str:
    if len(text) <= MAX_MSG_LENGTH:
        return text
    return text[: MAX_MSG_LENGTH - 20] + "\n\n_... (message tronqué)_"


_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I
)


async def _resolve_bottles(search_query: str) -> list[dict]:
    """Résout un search_query vers des bouteilles.

    - Si c'est un UUID (sélection depuis [CANDIDATS]) → lookup direct par ID.
    - Sinon → recherche flexible + déduplication.
    """
    if _UUID_RE.match(search_query.strip()):
        bottle = await queries.get_bottle_by_id(UUID(search_query.strip()))
        return [bottle] if bottle else []
    return _deduplicate_bottles(await flexible_search(search_query))


def _deduplicate_bottles(bottles: list[dict]) -> list[dict]:
    """Fusionne les entrées avec le même nom + millésime (quantités additionnées).

    Quand des doublons existent en base, on les présente comme une seule entrée
    pour simplifier l'UX. On conserve l'id de la première entrée pour les opérations.
    """
    seen: dict[tuple, dict] = {}
    for b in bottles:
        key = (b.get("name", "").lower(), b.get("vintage"))
        if key in seen:
            seen[key]["quantity"] = seen[key].get("quantity", 1) + b.get("quantity", 1)
        else:
            seen[key] = dict(b)
    return list(seen.values())


class WineManager:
    """Orchestre toutes les actions de gestion de cave."""

    async def handle_intent(self, intent: MistralIntent, phone_number: str, mistral_service: "MistralService") -> str:
        """Dispatch l'intent vers la méthode correspondante."""
        p = intent.parameters
        try:
            match intent.intent:
                case "add_bottle":
                    return await self.add_bottle(p)
                case "remove_bottle":
                    return await self.remove_bottle(p)
                case "search_bottles":
                    return await self.search_bottles(p)
                case "list_all":
                    return await self.list_all()
                case "get_stats":
                    return await self.get_stats()
                case "food_pairing":
                    return await self.food_pairing(p, mistral_service)
                case "maturity_check":
                    return await self.maturity_check()
                case "add_tasting_note":
                    return await self.add_tasting_note(p)
                case "view_history":
                    return await self.view_history(p)
                case "help":
                    # Utilise la réponse conversationnelle de Mistral si disponible
                    return intent.response_text or await self.help()
                case _:
                    return intent.response_text
        except Exception:
            logger.exception("Erreur dans handle_intent (intent=%s)", intent.intent)
            return "Oups, une erreur s'est produite 😓 Réessaie dans un instant."

    # ------------------------------------------------------------------ #
    # Bouteilles                                                           #
    # ------------------------------------------------------------------ #

    async def add_bottle(self, params: dict) -> str:
        """Ajoute une bouteille à la cave."""
        bottle = BottleCreate(
            name=params["name"],
            color=params["color"],
            region=params.get("region"),
            appellation=params.get("appellation"),
            producer=params.get("producer"),
            vintage=params.get("vintage"),
            grape_varieties=params.get("grape_varieties"),
            purchase_price=params.get("purchase_price"),
            quantity=params.get("quantity") or 1,
            storage_location=params.get("storage_location"),
            drink_from=params.get("drink_from"),
            drink_until=params.get("drink_until"),
            notes=params.get("notes"),
        )
        result = await queries.add_bottle(bottle)
        emoji = COLOR_EMOJI.get(bottle.color, "🍷")
        qty = bottle.quantity
        vintage_str = f" *{bottle.vintage}*" if bottle.vintage else ""
        lines = [f"{emoji} *{result['name']}*{vintage_str} ajouté{'e' if bottle.color in ('blanc','rosé') else ''} à ta cave ! ✅"]
        if bottle.producer:
            lines.append(f"🏰 {bottle.producer}")
        if bottle.region or bottle.appellation:
            lines.append(f"📍 {', '.join(filter(None, [bottle.appellation, bottle.region]))}")
        if qty > 1:
            lines.append(f"📦 {qty} bouteilles")
        if bottle.drink_from or bottle.drink_until:
            window = f"{bottle.drink_from or '?'} – {bottle.drink_until or '?'}"
            lines.append(f"⏳ Fenêtre de dégustation : {window}")

        return "\n".join(lines)

    async def remove_bottle(self, params: dict) -> str:
        """Retire une bouteille de la cave."""
        search_query = params.get("search_query", "")
        qty_to_remove = params.get("quantity_to_remove") or 1

        bottles = await _resolve_bottles(search_query)
        if not bottles:
            return f"Aucune bouteille trouvée pour *\"{search_query}\"* 🔍\nVérifie le nom ou utilise _rechercher_ pour explorer ta cave."

        if len(bottles) > 1:
            lines = [f"J'ai trouvé {len(bottles)} vins différents, lequel veux-tu retirer ?\n"]
            for i, b in enumerate(bottles[:8], 1):
                vintage_str = f" {b['vintage']}" if b.get("vintage") else ""
                loc = f" — {b['storage_location']}" if b.get("storage_location") else ""
                lines.append(f"{i}. {b['name']}{vintage_str}{loc} (x{b['quantity']})")
            # Stocker les UUIDs pour que Mistral puisse résoudre la sélection
            ids_context = ", ".join(f"{i+1}={b['id']}" for i, b in enumerate(bottles[:8]))
            lines.append(f"\n[CANDIDATS: {ids_context}]")
            lines.append("Précise le numéro ou le nom complet 🍷")
            return "\n".join(lines)

        bottle = bottles[0]
        result = await queries.decrement_quantity(bottle["id"], qty_to_remove)
        vintage_str = f" {bottle['vintage']}" if bottle.get("vintage") else ""
        name = f"*{bottle['name']}{vintage_str}*"

        if result.get("deleted"):
            # [BOUTEILLE_SUPPRIMEE] : contexte machine pour que Mistral puisse créer une note sans relookup DB
            supprimee_ctx = f"\n[BOUTEILLE_SUPPRIMEE: name={bottle['name']!r}, vintage={bottle.get('vintage')}]"
            return (
                f"🍷 {name} retiré de ta cave (dernière bouteille bue !).\n"
                f"Tu veux noter cette dégustation ? Dis-moi ta note sur 5 !"
                + supprimee_ctx
            )
        remaining = result["quantity"]
        return f"✅ {qty_to_remove} bouteille(s) de {name} retirée(s).\nIl t'en reste *{remaining}*."

    async def search_bottles(self, params: dict) -> str:
        """Recherche des bouteilles avec filtres."""
        bottles = await queries.search_bottles(
            query=params.get("query"),
            color=params.get("color"),
            region=params.get("region"),
            vintage_min=params.get("vintage_min"),
            vintage_max=params.get("vintage_max"),
            price_min=params.get("price_min"),
            price_max=params.get("price_max"),
            sort_by=params.get("sort_by"),
        )
        if not bottles:
            return "Aucune bouteille ne correspond à ta recherche 🔍\nEssaie avec d'autres critères."

        sort_by = params.get("sort_by", "")
        total_qty = sum(b.get("quantity", 1) for b in bottles)
        ref_str = f" ({len(bottles)} référence(s))" if len(bottles) != total_qty else ""
        lines = [f"🔍 *{total_qty} bouteille(s) trouvée(s)*{ref_str} :\n"]
        for b in bottles[:10]:
            emoji = COLOR_EMOJI.get(b.get("color", ""), "🍷")
            vintage_str = f" {b['vintage']}" if b.get("vintage") else ""
            qty = b.get("quantity", 1)
            lines.append(f"{emoji} *{b['name']}*{vintage_str} x{qty}")
            if b.get("region") or b.get("appellation"):
                lines.append(f"   📍 {', '.join(filter(None, [b.get('appellation'), b.get('region')]))}")
            if sort_by in ("price_desc", "price_asc") and b.get("purchase_price"):
                lines.append(f"   💶 {b['purchase_price']:.0f} €")

        if len(bottles) > 10:
            lines.append(f"\n_... et {len(bottles) - 10} autre(s). Affine ta recherche pour voir plus._")

        return _truncate("\n".join(lines))

    async def list_all(self) -> str:
        """Liste toute la cave groupée par couleur puis région."""
        bottles = await queries.list_all_bottles()
        if not bottles:
            return "Ta cave est vide pour l'instant 🥲\nCommence par ajouter une bouteille !"

        total = sum(b.get("quantity", 1) for b in bottles)
        lines = [f"🍾 *Ta cave — {total} bouteille(s)*\n"]

        # Grouper par couleur
        by_color: dict[str, list] = {}
        for b in bottles:
            color = b.get("color", "autre")
            by_color.setdefault(color, []).append(b)

        for color, items in by_color.items():
            emoji = COLOR_EMOJI.get(color, "🍷")
            subtotal = sum(b.get("quantity", 1) for b in items)
            lines.append(f"\n{emoji} *{color.capitalize()}* ({subtotal})")
            for b in items:
                vintage_str = f" {b['vintage']}" if b.get("vintage") else ""
                qty = b.get("quantity", 1)
                region_str = f" — {b['region']}" if b.get("region") else ""
                lines.append(f"  • {b['name']}{vintage_str}{region_str} x{qty}")

        return _truncate("\n".join(lines))

    async def get_stats(self) -> str:
        """Retourne les statistiques de la cave."""
        stats = await queries.get_stats()
        lines = [
            "📊 *Statistiques de ta cave*\n",
            f"🍾 *{stats['total_bottles']}* bouteilles ({stats['total_references']} références)",
        ]

        if stats["by_color"]:
            lines.append("\n*Répartition par couleur :*")
            for color, count in sorted(stats["by_color"].items(), key=lambda x: x[1], reverse=True):
                emoji = COLOR_EMOJI.get(color, "🍷")
                lines.append(f"  {emoji} {color.capitalize()} : {count}")

        if stats["top_regions"]:
            lines.append("\n*Top régions :*")
            for region, count in stats["top_regions"]:
                lines.append(f"  📍 {region} : {count}")

        if stats["vintage_range"]:
            v_min, v_max = stats["vintage_range"]
            lines.append(f"\n📅 Millésimes : *{v_min}* → *{v_max}*")

        if stats["total_value"]:
            lines.append(f"💶 Valeur estimée : *{stats['total_value']:.0f} €*")

        if stats["recent_tastings"]:
            lines.append("\n*Dernières dégustations :*")
            for t in stats["recent_tastings"][:3]:
                rating_str = f" {_stars(t['rating'])}" if t.get("rating") else ""
                lines.append(f"  🥃 {t['bottle_name']}{rating_str}")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Accords mets-vins                                                    #
    # ------------------------------------------------------------------ #

    async def food_pairing(self, params: dict, mistral_service: "MistralService") -> str:
        """Suggère des accords mets-vin depuis la cave."""
        dish = params.get("dish_description", "")
        bottles = await queries.list_all_bottles()
        return await mistral_service.get_food_pairing(dish, bottles)

    # ------------------------------------------------------------------ #
    # Maturité                                                             #
    # ------------------------------------------------------------------ #

    async def maturity_check(self) -> str:
        """Classe les vins selon leur fenêtre de dégustation."""
        bottles = await queries.list_all_bottles()
        current_year = date.today().year

        categories: dict[str, list] = {
            "À boire rapidement ⚠️": [],
            "Fenêtre optimale ✅": [],
            "Trop jeune 🌱": [],
            "Passé le pic 📉": [],
            "Sans info maturité": [],
        }

        for b in bottles:
            drink_from = b.get("drink_from")
            drink_until = b.get("drink_until")

            if not drink_from and not drink_until:
                categories["Sans info maturité"].append(b)
                continue

            if drink_until and current_year > drink_until:
                categories["Passé le pic 📉"].append(b)
            elif drink_until and current_year >= drink_until - 1:
                categories["À boire rapidement ⚠️"].append(b)
            elif drink_from and current_year < drink_from:
                categories["Trop jeune 🌱"].append(b)
            else:
                categories["Fenêtre optimale ✅"].append(b)

        lines = [f"⏳ *Maturité de ta cave ({current_year})*\n"]
        order = ["À boire rapidement ⚠️", "Fenêtre optimale ✅", "Trop jeune 🌱", "Passé le pic 📉"]

        for cat in order:
            items = categories[cat]
            if not items:
                continue
            lines.append(f"\n*{cat}*")
            for b in items:
                vintage_str = f" {b['vintage']}" if b.get("vintage") else ""
                window = f"{b.get('drink_from') or '?'}–{b.get('drink_until') or '?'}"
                lines.append(f"  • {b['name']}{vintage_str} ({window}) x{b.get('quantity', 1)}")

        no_info = categories["Sans info maturité"]
        if no_info:
            lines.append(f"\n_({len(no_info)} bouteille(s) sans données de maturité)_")

        return _truncate("\n".join(lines))

    # ------------------------------------------------------------------ #
    # Dégustations                                                         #
    # ------------------------------------------------------------------ #

    async def add_tasting_note(self, params: dict) -> str:
        """Enregistre une note de dégustation et décrémente la quantité."""
        search_query = params.get("search_query", "")
        bottle_already_removed = params.get("bottle_already_removed", False)

        if bottle_already_removed:
            # Bouteille déjà supprimée (dernière unité retirée juste avant) : créer la note sans DB lookup
            note = TastingNoteCreate(
                bottle_id=None,
                bottle_name=search_query,
                rating=params.get("rating"),
                tasting_notes=params.get("tasting_notes"),
                food_pairing=params.get("food_pairing"),
                occasion=params.get("occasion"),
            )
            await queries.add_tasting_note(note)
            lines = [f"🥃 Dégustation de *{search_query}* enregistrée !"]
            if note.rating:
                lines.append(f"Note : {_stars(note.rating)} ({note.rating}/5)")
            if note.tasting_notes:
                lines.append(f"_{note.tasting_notes}_")
            return "\n".join(lines)

        bottles = await _resolve_bottles(search_query)

        if not bottles:
            return f"Aucune bouteille trouvée pour *\"{search_query}\"* 🔍"

        if len(bottles) > 1:
            lines = ["Plusieurs vins correspondent, lequel as-tu dégusté ?\n"]
            for i, b in enumerate(bottles[:6], 1):
                vintage_str = f" {b['vintage']}" if b.get("vintage") else ""
                loc = f" — {b['storage_location']}" if b.get("storage_location") else ""
                lines.append(f"{i}. {b['name']}{vintage_str}{loc}")
            ids_context = ", ".join(f"{i+1}={b['id']}" for i, b in enumerate(bottles[:6]))
            lines.append(f"\n[CANDIDATS: {ids_context}]")
            return "\n".join(lines)

        bottle = bottles[0]
        note = TastingNoteCreate(
            bottle_id=bottle["id"],
            bottle_name=bottle["name"],
            rating=params.get("rating"),
            tasting_notes=params.get("tasting_notes"),
            food_pairing=params.get("food_pairing"),
            occasion=params.get("occasion"),
        )
        await queries.add_tasting_note(note)
        await queries.decrement_quantity(bottle["id"], 1)

        vintage_str = f" {bottle['vintage']}" if bottle.get("vintage") else ""
        lines = [f"🥃 Dégustation de *{bottle['name']}{vintage_str}* enregistrée !"]
        if note.rating:
            lines.append(f"Note : {_stars(note.rating)} ({note.rating}/5)")
        if note.tasting_notes:
            lines.append(f"_{note.tasting_notes}_")
        return "\n".join(lines)

    async def view_history(self, params: dict) -> str:
        """Affiche l'historique des dégustations."""
        limit = params.get("limit") or 10
        min_rating = params.get("min_rating")
        entries = await queries.list_tasting_notes(limit=limit, min_rating=min_rating)

        if not entries:
            return "Aucune dégustation enregistrée pour l'instant 🥂"

        lines = [f"🥃 *Historique des dégustations* ({len(entries)})\n"]
        for e in entries:
            rating_str = f" {_stars(e['rating'])}" if e.get("rating") else ""
            lines.append(f"• *{e['bottle_name']}*{rating_str}")
            lines.append(f"  📅 {e['tasted_at']}")
            if e.get("tasting_notes"):
                lines.append(f"  _{e['tasting_notes']}_")

        return _truncate("\n".join(lines))

    # ------------------------------------------------------------------ #
    # Aide                                                                 #
    # ------------------------------------------------------------------ #

    async def help(self) -> str:
        """Retourne le message d'aide."""
        return (
            "🍷 *Sommelier — Aide*\n\n"
            "Voici ce que je sais faire :\n\n"
            "*📦 Gestion de cave*\n"
            "• Ajouter une bouteille\n"
            "• Retirer / marquer comme bue\n"
            "• Rechercher (par nom, région, couleur, millésime...)\n"
            "• Lister toute la cave\n\n"
            "*📊 Analyses*\n"
            "• Statistiques de ta cave\n"
            "• Vérifier la maturité des vins\n\n"
            "*🍽️ Accords & dégustations*\n"
            "• Accord mets-vin (dis-moi ton plat !)\n"
            "• Enregistrer une note de dégustation\n"
            "• Voir l'historique des dégustations\n\n"
            "*📸 Photo*\n"
            "• Envoie la photo d'une étiquette pour identifier et ajouter le vin\n\n"
            "_Parle-moi naturellement, je comprends le français !_ 🇫🇷"
        )
