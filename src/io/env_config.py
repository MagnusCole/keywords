"""
env_config.py — Google Ads environment and credential loader

Provides helpers to load Google Ads credentials from environment variables or .env file.
"""

import os
from pathlib import Path


def load_dotenv_file(dotenv_path: str | Path = ".env") -> None:
    """Load environment variables from a .env file if present."""
    dotenv_path = Path(dotenv_path)
    if dotenv_path.exists():
        with dotenv_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def get_google_ads_credentials() -> dict[str, str]:
    """Get Google Ads credentials from environment variables."""
    keys = [
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
    ]
    creds = {}
    for key in keys:
        val = os.getenv(key)
        if not val:
            raise RuntimeError(f"Missing required Google Ads credential: {key}")
        creds[key.lower().replace("google_ads_", "")] = val
    return creds
