"""
Environment configuration for Google Ads API.
Loads .env file and validates required credentials.
"""

import os
from pathlib import Path


def load_dotenv_file() -> None:
    """Load .env file if it exists."""
    env_file = Path(".env")
    if not env_file.exists():
        return

    try:
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        os.environ[key] = value
    except Exception as e:
        print(f"Warning: Failed to load .env file: {e}")


def get_google_ads_credentials() -> dict[str, str | None]:
    """Get Google Ads credentials from environment."""
    # Load .env file first
    load_dotenv_file()

    return {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "customer_id": os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
    }


def validate_credentials() -> tuple[bool, list[str]]:
    """Validate that all required credentials are present."""
    creds = get_google_ads_credentials()

    required_fields = [
        "developer_token",
        "client_id",
        "client_secret",
        "refresh_token",
        "customer_id",
    ]

    missing = []
    for field in required_fields:
        value = creds.get(field)
        if not value or value == "":
            missing.append(field.upper())

    return len(missing) == 0, missing


def print_credentials_status() -> None:
    """Print the current status of Google Ads credentials."""
    creds = get_google_ads_credentials()

    print("Google Ads API Credentials Status:")
    print("=" * 40)

    for key, value in creds.items():
        field_name = key.replace("_", " ").title()
        if value and value != "":
            # Show masked version for security
            if len(value) > 20:
                masked = f"{value[:8]}...{value[-4:]}"
            else:
                masked = f"{value[:4]}..."
            print(f"✅ {field_name}: {masked}")
        else:
            print(f"❌ {field_name}: NOT SET")

    is_valid, missing = validate_credentials()
    print("=" * 40)

    if is_valid:
        print("✅ All required credentials are configured")
    else:
        print(f"❌ Missing required credentials: {', '.join(missing)}")


if __name__ == "__main__":
    print_credentials_status()
