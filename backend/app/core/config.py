from pathlib import Path

from dotenv import dotenv_values
from pydantic_settings import BaseSettings

# Resolve .env relative to the backend/ directory (two levels up from this file)
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

# Load .env manually — pydantic-settings struggles with spaces in paths
_env_vals = dotenv_values(str(_ENV_FILE)) if _ENV_FILE.exists() else {}


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://sage:sage_dev@localhost:5432/sage"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Anthropic
    anthropic_api_key: str = ""

    # WhatsApp
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""

    # Slack
    slack_bot_token: str = ""
    slack_app_token: str = ""

    # App
    app_name: str = "Sage"
    debug: bool = False
    sql_echo: bool = False  # Set True to see SQL queries (noisy in CLI)

    model_config = {"env_file": str(_ENV_FILE), "env_file_encoding": "utf-8"}


settings = Settings(**{k.lower(): v for k, v in _env_vals.items() if v})
