import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False

try:
    from dotenv import load_dotenv  # type: ignore
    # Load default .env first
    load_dotenv()
    # Then optionally load user keys from local files if present
    for candidate in (Path(".env.local"), Path("keys.env")):
        if candidate.exists():
            load_dotenv(dotenv_path=candidate, override=True)
except Exception:
    pass


def _get_secret(key: str, default: str = "") -> str:
    """Get value from Streamlit secrets or environment variable."""
    if _HAS_STREAMLIT:
        try:
            # Try to get from Streamlit secrets (for deployed apps)
            if hasattr(st, "secrets") and key in st.secrets:
                return str(st.secrets[key])
        except Exception:
            pass
    # Fall back to environment variable
    return os.environ.get(key, default)


@dataclass(frozen=True)
class Settings:
    grok_api_key: str
    grok_base_url: str
    grok_model: str

    gemini_api_key: str
    gemini_model: str

    amadeus_api_key: str
    amadeus_api_secret: str
    amadeus_env: str

    default_currency: str


def get_settings() -> Settings:
    return Settings(
        grok_api_key=_get_secret("GROK_API_KEY", ""),
        grok_base_url=_get_secret("GROK_BASE_URL", "https://api.x.ai/v1"),
        grok_model=_get_secret("GROK_MODEL", "grok-2-latest"),
        gemini_api_key=_get_secret("GEMINI_API_KEY", ""),
        gemini_model=_get_secret("GEMINI_MODEL", "gemini-1.5-pro"),
        amadeus_api_key=_get_secret("AMADEUS_API_KEY", ""),
        amadeus_api_secret=_get_secret("AMADEUS_API_SECRET", ""),
        amadeus_env=_get_secret("AMADEUS_ENV", "production"),
        default_currency=_get_secret("DEFAULT_CURRENCY", "USD"),
    )


