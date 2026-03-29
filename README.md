# Spotify MCP Server

A Model Context Protocol (MCP) server that connects Claude.ai to your Spotify account. Claude can analyze your listening taste, get recommendations, and create playlists conversationally.

## Tools

| Tool | Description |
|------|-------------|
| `get_top_tracks` | Get your top tracks by time range |
| `get_top_artists` | Get your top artists by time range |
| `get_recently_played` | Get recently played tracks |
| `get_audio_features` | Get audio features (energy, valence, tempo, etc.) for tracks |
| `get_recommendations` | Get recommendations from seed tracks/artists/genres |
| `create_playlist` | Create a new playlist |
| `add_tracks_to_playlist` | Add tracks to a playlist |
| `get_user_playlists` | List your playlists |
| `search_tracks` | Search for tracks |
| `analyze_taste_profile` | Full taste analysis: top tracks, artists, audio features, genres, and summary |

## Setup

### 1. Create a Spotify App

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Set the redirect URI to `http://127.0.0.1:8888/callback` (use `127.0.0.1`, not `localhost` \u2014 Spotify blocks `localhost` on app creation)
4. Copy your **Client ID** and **Client Secret**

### 2. Configure Environment

```bash
cp .env.example .env
```

Fill in `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `.env`.

### 3. One-Time Auth (Get Refresh Token)

```bash
pip install -r requirements.txt
python auth.py
```

This opens Spotify's authorization page. After you approve, paste the redirect URL back into the terminal. The script prints your refresh token \u2014 add it to `.env` as `SPOTIFY_REFRESH_TOKEN`.

Once the refresh token is saved, you never need to run `auth.py` again. The server auto-refreshes the token on every start.

### 4. Run Locally

```bash
python server.py
```

The server starts at `http://localhost:8000/sse`.

### 5. Connect to Claude.ai

1. Go to Claude.ai \u2192 **Settings** \u2192 **Connectors**
2. Click **Add Custom Connector**
3. Paste the SSE URL: `http://localhost:8000/sse` (or your deployed HTTPS URL)

### 6. Deploy to Railway (Optional)

1. Push this repo to GitHub
2. Connect the repo in [Railway](https://railway.app)
3. Add these environment variables in the Railway dashboard:
   - `SPOTIFY_CLIENT_ID`
   - `SPOTIFY_CLIENT_SECRET`
   - `SPOTIFY_REFRESH_TOKEN`
   - `PORT` (Railway sets this automatically)
4. Deploy \u2014 Railway gives you a public HTTPS URL
5. Use that URL + `/sse` as the connector URL in Claude.ai

## Example Usage

> "Analyze my music taste and build me a late night focus playlist"

Claude will call `analyze_taste_profile` to understand your preferences, then use `get_recommendations` with appropriate targets (low energy, high acousticness), `create_playlist`, and `add_tracks_to_playlist` to build it.

## How It Works

The server uses Spotify's OAuth 2.0 with a **refresh token** strategy. You authenticate once with `auth.py` to get a long-lived refresh token. The server pre-seeds spotipy's `MemoryCacheHandler` with this token and `expires_at=0`, which forces an immediate token refresh on startup \u2014 no browser, no interactive prompt. The token auto-refreshes on every expiry.
