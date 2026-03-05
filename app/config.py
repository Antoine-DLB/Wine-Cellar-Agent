"""Configuration de l'application via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application chargés depuis les variables d'environnement."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # WhatsApp Business API
    whatsapp_token: str
    whatsapp_phone_number_id: str
    whatsapp_verify_token: str

    # Mistral AI
    mistral_api_key: str

    # Supabase
    supabase_url: str
    supabase_key: str

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"
    conversation_history_limit: int = 10
