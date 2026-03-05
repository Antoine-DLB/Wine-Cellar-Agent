"""Modèles Pydantic pour les bouteilles et les dégustations."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# Bottles
# ============================================================

class BottleCreate(BaseModel):
    """Modèle pour la création d'une bouteille."""

    name: str
    color: str
    region: Optional[str] = None
    appellation: Optional[str] = None
    producer: Optional[str] = None
    vintage: Optional[int] = None
    grape_varieties: Optional[list[str]] = None
    purchase_price: Optional[float] = None
    purchase_date: Optional[date] = None
    quantity: int = 1
    storage_location: Optional[str] = None
    drink_from: Optional[int] = None
    drink_until: Optional[int] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None


class BottleUpdate(BaseModel):
    """Modèle pour la mise à jour d'une bouteille (tous les champs optionnels)."""

    name: Optional[str] = None
    color: Optional[str] = None
    region: Optional[str] = None
    appellation: Optional[str] = None
    producer: Optional[str] = None
    vintage: Optional[int] = None
    grape_varieties: Optional[list[str]] = None
    purchase_price: Optional[float] = None
    purchase_date: Optional[date] = None
    quantity: Optional[int] = None
    storage_location: Optional[str] = None
    drink_from: Optional[int] = None
    drink_until: Optional[int] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None


class BottleResponse(BottleCreate):
    """Modèle de réponse complet avec métadonnées."""

    id: UUID
    created_at: datetime
    updated_at: datetime


# ============================================================
# Tasting log
# ============================================================

class TastingNoteCreate(BaseModel):
    """Modèle pour ajouter une note de dégustation."""

    bottle_id: Optional[UUID] = None
    bottle_name: str
    tasted_at: date = Field(default_factory=date.today)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    tasting_notes: Optional[str] = None
    food_pairing: Optional[str] = None
    occasion: Optional[str] = None


class TastingNoteResponse(TastingNoteCreate):
    """Modèle de réponse avec id."""

    id: UUID
    created_at: datetime

