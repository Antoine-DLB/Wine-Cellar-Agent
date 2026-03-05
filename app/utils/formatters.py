"""Fonctions utilitaires de formatage pour les messages WhatsApp."""

MAX_LENGTH = 4096

COLOR_EMOJI: dict[str, str] = {
    "rouge": "🔴",
    "blanc": "⚪",
    "rosé": "🌸",
    "champagne": "🥂",
    "mousseux": "🫧",
    "liquoreux": "🍯",
}


def color_emoji(color: str) -> str:
    """Retourne l'emoji correspondant à la couleur du vin."""
    return COLOR_EMOJI.get(color.lower(), "🍷")


def rating_stars(rating: int) -> str:
    """Retourne une représentation en étoiles (ex: ⭐⭐⭐⭐☆)."""
    rating = max(1, min(5, rating))
    return "⭐" * rating + "☆" * (5 - rating)


def truncate_message(text: str, max_length: int = MAX_LENGTH) -> str:
    """Tronque le message si nécessaire avec une indication de suite."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 25] + "\n\n_... (message tronqué)_"


def format_bottle(bottle: dict) -> str:
    """Formate une bouteille sur 2-3 lignes avec emojis."""
    emoji = color_emoji(bottle.get("color", ""))
    vintage_str = f" {bottle['vintage']}" if bottle.get("vintage") else ""
    qty = bottle.get("quantity", 1)
    lines = [f"{emoji} *{bottle['name']}*{vintage_str} x{qty}"]

    location = list(filter(None, [bottle.get("appellation"), bottle.get("region")]))
    if location:
        lines.append(f"   📍 {', '.join(location)}")

    if bottle.get("producer"):
        lines.append(f"   🏰 {bottle['producer']}")

    if bottle.get("drink_from") or bottle.get("drink_until"):
        window = f"{bottle.get('drink_from') or '?'}–{bottle.get('drink_until') or '?'}"
        lines.append(f"   ⏳ {window}")

    return "\n".join(lines)


def format_bottle_list(bottles: list[dict], title: str) -> str:
    """Formate une liste de bouteilles groupée, avec pagination si > 10."""
    if not bottles:
        return f"*{title}*\n\n_Aucune bouteille trouvée._"

    lines = [f"*{title}* ({len(bottles)} résultat(s))\n"]
    displayed = bottles[:10]

    for bottle in displayed:
        lines.append(format_bottle(bottle))

    if len(bottles) > 10:
        lines.append(f"\n_... et {len(bottles) - 10} autre(s). Affine ta recherche._")

    return truncate_message("\n".join(lines))


def format_stats(stats: dict) -> str:
    """Formate les statistiques de la cave de manière visuelle."""
    lines = [
        "📊 *Statistiques de ta cave*\n",
        f"🍾 *{stats['total_bottles']}* bouteilles  |  *{stats['total_references']}* références",
    ]

    if stats.get("by_color"):
        lines.append("\n*Par couleur :*")
        for col, count in sorted(stats["by_color"].items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {color_emoji(col)} {col.capitalize()} — {count}")

    if stats.get("top_regions"):
        lines.append("\n*Top régions :*")
        for region, count in stats["top_regions"]:
            lines.append(f"  📍 {region} — {count}")

    if stats.get("vintage_range"):
        v_min, v_max = stats["vintage_range"]
        lines.append(f"\n📅 Millésimes : *{v_min}* → *{v_max}*")

    if stats.get("total_value"):
        lines.append(f"💶 Valeur estimée : *{stats['total_value']:.0f} €*")

    if stats.get("recent_tastings"):
        lines.append("\n*Dernières dégustations :*")
        for t in stats["recent_tastings"][:3]:
            stars = f" {rating_stars(t['rating'])}" if t.get("rating") else ""
            lines.append(f"  🥃 {t['bottle_name']}{stars}")

    return "\n".join(lines)


def format_tasting_log(entries: list[dict]) -> str:
    """Formate l'historique des dégustations."""
    if not entries:
        return "Aucune dégustation enregistrée pour l'instant 🥂"

    lines = [f"🥃 *Historique des dégustations* ({len(entries)})\n"]
    for e in entries:
        stars = f" {rating_stars(e['rating'])}" if e.get("rating") else ""
        lines.append(f"• *{e['bottle_name']}*{stars}")
        lines.append(f"  📅 {e['tasted_at']}")
        if e.get("tasting_notes"):
            lines.append(f"  _{e['tasting_notes']}_")
        if e.get("food_pairing"):
            lines.append(f"  🍽️ {e['food_pairing']}")

    return truncate_message("\n".join(lines))


def format_maturity_report(categories: dict) -> str:
    """Formate le rapport de maturité par catégorie d'urgence."""
    order = ["À boire rapidement ⚠️", "Fenêtre optimale ✅", "Trop jeune 🌱", "Passé le pic 📉"]
    lines = []

    for cat in order:
        items = categories.get(cat, [])
        if not items:
            continue
        lines.append(f"\n*{cat}*")
        for b in items:
            vintage_str = f" {b['vintage']}" if b.get("vintage") else ""
            window = f"{b.get('drink_from') or '?'}–{b.get('drink_until') or '?'}"
            qty = b.get("quantity", 1)
            lines.append(f"  • {b['name']}{vintage_str} ({window}) x{qty}")

    no_info = categories.get("Sans info maturité", [])
    if no_info:
        lines.append(f"\n_({len(no_info)} bouteille(s) sans données de maturité)_")

    if not lines:
        return "Aucune bouteille avec données de maturité 🤷"

    return truncate_message("\n".join(lines))
