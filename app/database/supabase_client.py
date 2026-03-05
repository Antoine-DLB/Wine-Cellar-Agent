"""Client Supabase singleton."""

import logging
from functools import lru_cache

from supabase import Client, create_client

from app.config import Settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Retourne le client Supabase (singleton via lru_cache)."""
    settings = Settings()
    logger.info("Initialisation du client Supabase")
    return create_client(settings.supabase_url, settings.supabase_key)
