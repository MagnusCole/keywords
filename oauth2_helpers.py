# Downloaded from https://github.com/googleads/google-ads-python/blob/main/google/ads/googleads/oauth2_helpers.py
# Minimal version for refresh token generation

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/adwords"]


def main():
    print("Google Ads API OAuth2 Helper\n")
    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()
    print("\nA browser window will open for authentication...")
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        SCOPES,
    )
    creds = flow.run_local_server(port=0)
    print("\nYour refresh token:")
    print(creds.refresh_token)
    print("\nPaste this in your .env as GOOGLE_ADS_REFRESH_TOKEN.")


if __name__ == "__main__":
    main()
