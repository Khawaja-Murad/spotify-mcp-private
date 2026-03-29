"""One-time OAuth script to obtain a Spotify refresh token."""

import os
import sys
import webbrowser
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
import spotipy

SCOPES = (
    "user-top-read "
    "user-read-recently-played "
    "playlist-modify-public "
    "playlist-modify-private "
    "playlist-read-private "
    "user-library-read"
)


def main():
    load_dotenv()

    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("ERROR: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env")
        sys.exit(1)

    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPES,
        cache_path=".spotify_auth_cache",
        open_browser=False,
    )

    auth_url = auth_manager.get_authorize_url()

    print("\n=== Spotify Authorization ===\n")
    print("Open this URL in your browser to authorize:\n")
    print(auth_url)
    print()

    try:
        webbrowser.open(auth_url)
        print("(Attempted to open in your default browser)")
    except Exception:
        print("(Could not open browser automatically \u2014 use the URL above)")

    print()
    redirect_response = input("Paste the full redirect URL here: ").strip()

    if not redirect_response:
        print("ERROR: No URL provided.")
        sys.exit(1)

    try:
        parsed = urlparse(redirect_response)
        code = parse_qs(parsed.query).get("code")
        if not code:
            print("ERROR: No 'code' parameter found in the URL.")
            sys.exit(1)
        code = code[0]
    except Exception as e:
        print(f"ERROR: Could not parse URL: {e}")
        sys.exit(1)

    try:
        token_info = auth_manager.get_access_token(code, as_dict=True)
    except Exception as e:
        print(f"ERROR: Token exchange failed: {e}")
        sys.exit(1)

    refresh_token = token_info.get("refresh_token")
    if not refresh_token:
        print("ERROR: No refresh_token in response.")
        sys.exit(1)

    print("\n=== Success! ===\n")
    print(f"Your refresh token:\n\n  {refresh_token}\n")
    print("Add this to your .env file as:")
    print(f"  SPOTIFY_REFRESH_TOKEN={refresh_token}\n")

    # Verify the token works
    try:
        sp = spotipy.Spotify(auth_manager=auth_manager)
        user = sp.current_user()
        print(f"Verified! Logged in as: {user['display_name']} ({user['id']})")
    except Exception as e:
        print(f"Warning: Could not verify token: {e}")

    # Clean up cache file
    try:
        os.remove(".spotify_auth_cache")
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    main()
