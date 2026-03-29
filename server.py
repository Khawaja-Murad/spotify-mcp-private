"""Spotify MCP Server — exposes Spotify data and actions as MCP tools."""

import json
import logging
import os
from collections import Counter

import spotipy
import uvicorn
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import MemoryCacheHandler
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spotify-mcp")

SCOPES = (
    "user-top-read "
    "user-read-recently-played "
    "playlist-modify-public "
    "playlist-modify-private "
    "playlist-read-private "
    "user-library-read"
)

# --- Spotify client setup ---

token_info = {
    "access_token": "placeholder",
    "refresh_token": os.environ["SPOTIFY_REFRESH_TOKEN"],
    "expires_at": 0,
    "token_type": "Bearer",
    "scope": SCOPES,
}

auth_manager = SpotifyOAuth(
    client_id=os.environ["SPOTIFY_CLIENT_ID"],
    client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
    scope=SCOPES,
    cache_handler=MemoryCacheHandler(token_info=token_info),
    open_browser=False,
)

sp = spotipy.Spotify(auth_manager=auth_manager)

# --- MCP Server ---

server = Server("spotify-mcp")
session_manager = StreamableHTTPSessionManager(
    app=server,
    stateless=True,
    json_response=True,
)


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_top_tracks",
            description="Get the user's top tracks on Spotify.",
            inputSchema={
                "type": "object",
                "properties": {
                    "time_range": {
                        "type": "string",
                        "enum": ["short_term", "medium_term", "long_term"],
                        "description": "Time range: short_term (~4 weeks), medium_term (~6 months), long_term (all time). Default: medium_term.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of tracks to return (1-50). Default: 20.",
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
            },
        ),
        Tool(
            name="get_top_artists",
            description="Get the user's top artists on Spotify.",
            inputSchema={
                "type": "object",
                "properties": {
                    "time_range": {
                        "type": "string",
                        "enum": ["short_term", "medium_term", "long_term"],
                        "description": "Time range: short_term (~4 weeks), medium_term (~6 months), long_term (all time). Default: medium_term.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of artists to return (1-50). Default: 20.",
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
            },
        ),
        Tool(
            name="get_recently_played",
            description="Get the user's recently played tracks on Spotify.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of tracks to return (1-50). Default: 20.",
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
            },
        ),
        Tool(
            name="get_audio_features",
            description="Get audio features (energy, valence, danceability, tempo, etc.) for one or more tracks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of Spotify track IDs or URIs (e.g. 'spotify:track:xxx' or bare ID).",
                    },
                },
                "required": ["track_ids"],
            },
        ),
        Tool(
            name="get_recommendations",
            description="Get track recommendations based on seed tracks, artists, or genres. Total seeds must be 1-5.",
            inputSchema={
                "type": "object",
                "properties": {
                    "seed_tracks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of seed track IDs.",
                    },
                    "seed_artists": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of seed artist IDs.",
                    },
                    "seed_genres": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of seed genres.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of recommendations (1-100). Default: 20.",
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "target_energy": {
                        "type": "number",
                        "description": "Target energy (0.0-1.0).",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "target_valence": {
                        "type": "number",
                        "description": "Target valence/positivity (0.0-1.0).",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "target_danceability": {
                        "type": "number",
                        "description": "Target danceability (0.0-1.0).",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "target_tempo": {
                        "type": "number",
                        "description": "Target tempo in BPM.",
                    },
                    "target_acousticness": {
                        "type": "number",
                        "description": "Target acousticness (0.0-1.0).",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
            },
        ),
        Tool(
            name="create_playlist",
            description="Create a new Spotify playlist for the current user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the playlist.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Playlist description. Default: empty.",
                    },
                    "public": {
                        "type": "boolean",
                        "description": "Whether the playlist is public. Default: false.",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="add_tracks_to_playlist",
            description="Add tracks to a Spotify playlist.",
            inputSchema={
                "type": "object",
                "properties": {
                    "playlist_id": {
                        "type": "string",
                        "description": "The Spotify playlist ID.",
                    },
                    "track_uris": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of Spotify track URIs or IDs to add.",
                    },
                },
                "required": ["playlist_id", "track_uris"],
            },
        ),
        Tool(
            name="get_user_playlists",
            description="Get the current user's playlists.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of playlists to return (1-50). Default: 20.",
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
            },
        ),
        Tool(
            name="search_tracks",
            description="Search for tracks on Spotify.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (1-50). Default: 10.",
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="analyze_taste_profile",
            description="Analyze the user's music taste: top tracks, artists, audio features, genres, and a human-readable summary.",
            inputSchema={
                "type": "object",
                "properties": {
                    "time_range": {
                        "type": "string",
                        "enum": ["short_term", "medium_term", "long_term"],
                        "description": "Time range for analysis. Default: medium_term.",
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        result = _handle_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        logger.exception(f"Error in tool '{name}'")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


def _handle_tool(name: str, arguments: dict):
    if name == "get_top_tracks":
        return _get_top_tracks(arguments)
    elif name == "get_top_artists":
        return _get_top_artists(arguments)
    elif name == "get_recently_played":
        return _get_recently_played(arguments)
    elif name == "get_audio_features":
        return _get_audio_features(arguments)
    elif name == "get_recommendations":
        return _get_recommendations(arguments)
    elif name == "create_playlist":
        return _create_playlist(arguments)
    elif name == "add_tracks_to_playlist":
        return _add_tracks_to_playlist(arguments)
    elif name == "get_user_playlists":
        return _get_user_playlists(arguments)
    elif name == "search_tracks":
        return _search_tracks(arguments)
    elif name == "analyze_taste_profile":
        return _analyze_taste_profile(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


# --- Tool implementations ---


def _get_top_tracks(args: dict) -> list[dict]:
    time_range = args.get("time_range", "medium_term")
    limit = args.get("limit", 20)
    results = sp.current_user_top_tracks(time_range=time_range, limit=limit)
    return [
        {
            "name": t["name"],
            "artists": [a["name"] for a in t["artists"]],
            "album": t["album"]["name"],
            "uri": t["uri"],
            "id": t["id"],
            "popularity": t["popularity"],
        }
        for t in results["items"]
    ]


def _get_top_artists(args: dict) -> list[dict]:
    time_range = args.get("time_range", "medium_term")
    limit = args.get("limit", 20)
    results = sp.current_user_top_artists(time_range=time_range, limit=limit)
    return [
        {
            "name": a["name"],
            "genres": a["genres"],
            "popularity": a["popularity"],
            "id": a["id"],
            "uri": a["uri"],
        }
        for a in results["items"]
    ]


def _get_recently_played(args: dict) -> list[dict]:
    limit = args.get("limit", 20)
    results = sp.current_user_recently_played(limit=limit)
    return [
        {
            "name": item["track"]["name"],
            "artists": [a["name"] for a in item["track"]["artists"]],
            "played_at": item["played_at"],
            "uri": item["track"]["uri"],
            "id": item["track"]["id"],
        }
        for item in results["items"]
    ]


def _get_audio_features(args: dict) -> list:
    track_ids = args["track_ids"]
    # Strip URI prefix if present
    cleaned = [tid.replace("spotify:track:", "") for tid in track_ids]
    return sp.audio_features(cleaned)


def _get_recommendations(args: dict) -> list[dict]:
    kwargs = {}
    if "seed_tracks" in args:
        kwargs["seed_tracks"] = args["seed_tracks"]
    if "seed_artists" in args:
        kwargs["seed_artists"] = args["seed_artists"]
    if "seed_genres" in args:
        kwargs["seed_genres"] = args["seed_genres"]
    kwargs["limit"] = args.get("limit", 20)

    for param in ["target_energy", "target_valence", "target_danceability", "target_tempo", "target_acousticness"]:
        if param in args:
            kwargs[param] = args[param]

    results = sp.recommendations(**kwargs)
    return [
        {
            "name": t["name"],
            "artists": [a["name"] for a in t["artists"]],
            "uri": t["uri"],
            "id": t["id"],
            "popularity": t["popularity"],
        }
        for t in results["tracks"]
    ]


def _create_playlist(args: dict) -> dict:
    name = args["name"]
    description = args.get("description", "")
    public = args.get("public", False)
    user = sp.current_user()
    playlist = sp.user_playlist_create(
        user=user["id"],
        name=name,
        public=public,
        description=description,
    )
    return {
        "id": playlist["id"],
        "name": playlist["name"],
        "url": playlist["external_urls"]["spotify"],
        "uri": playlist["uri"],
    }


def _add_tracks_to_playlist(args: dict) -> dict:
    playlist_id = args["playlist_id"]
    track_uris = args["track_uris"]

    # Normalize: add URI prefix if bare IDs
    normalized = []
    for uri in track_uris:
        if not uri.startswith("spotify:track:"):
            uri = f"spotify:track:{uri}"
        normalized.append(uri)

    # Batch in chunks of 100
    total_added = 0
    for i in range(0, len(normalized), 100):
        batch = normalized[i : i + 100]
        sp.playlist_add_items(playlist_id, batch)
        total_added += len(batch)

    return {"success": True, "tracks_added": total_added}


def _get_user_playlists(args: dict) -> list[dict]:
    limit = args.get("limit", 20)
    results = sp.current_user_playlists(limit=limit)
    return [
        {
            "name": p["name"],
            "id": p["id"],
            "track_count": p["tracks"]["total"],
            "public": p["public"],
            "uri": p["uri"],
            "url": p["external_urls"]["spotify"],
        }
        for p in results["items"]
    ]


def _search_tracks(args: dict) -> list[dict]:
    query = args["query"]
    limit = args.get("limit", 10)
    results = sp.search(q=query, type="track", limit=limit)
    return [
        {
            "name": t["name"],
            "artists": [a["name"] for a in t["artists"]],
            "album": t["album"]["name"],
            "uri": t["uri"],
            "id": t["id"],
            "popularity": t["popularity"],
        }
        for t in results["tracks"]["items"]
    ]


def _analyze_taste_profile(args: dict) -> dict:
    time_range = args.get("time_range", "medium_term")

    # Fetch top tracks and artists
    top_tracks_resp = sp.current_user_top_tracks(time_range=time_range, limit=50)
    top_artists_resp = sp.current_user_top_artists(time_range=time_range, limit=50)

    tracks = top_tracks_resp["items"]
    artists = top_artists_resp["items"]

    # Audio features
    track_ids = [t["id"] for t in tracks]
    audio_features_raw = sp.audio_features(track_ids)
    audio_features = [af for af in audio_features_raw if af is not None]

    # Compute averages
    feature_keys = ["energy", "valence", "danceability", "acousticness", "instrumentalness", "speechiness", "tempo"]
    avg_features = {}
    if audio_features:
        for key in feature_keys:
            avg_features[key] = round(sum(af[key] for af in audio_features) / len(audio_features), 4)

    # Genre counts
    genre_counter = Counter()
    for artist in artists:
        for genre in artist["genres"]:
            genre_counter[genre] += 1
    top_genres = dict(genre_counter.most_common(15))

    # Taste summary
    taste_summary = {}
    if avg_features:
        e = avg_features.get("energy", 0.5)
        taste_summary["energy"] = "low" if e < 0.4 else ("medium" if e <= 0.7 else "high")

        v = avg_features.get("valence", 0.5)
        taste_summary["mood"] = "dark/melancholic" if v < 0.4 else ("mixed" if v <= 0.6 else "upbeat/positive")

        d = avg_features.get("danceability", 0.5)
        taste_summary["danceability"] = "not danceable" if d < 0.5 else ("moderate" if d <= 0.7 else "very danceable")

        a = avg_features.get("acousticness", 0.5)
        taste_summary["acoustic_vs_electronic"] = "acoustic" if a > 0.5 else "electronic/produced"

        taste_summary["avg_tempo_bpm"] = round(avg_features.get("tempo", 0))

    # Format track/artist summaries
    top_tracks_summary = [
        {
            "name": t["name"],
            "artists": [a["name"] for a in t["artists"]],
            "id": t["id"],
            "uri": t["uri"],
        }
        for t in tracks[:20]
    ]
    top_artists_summary = [
        {
            "name": a["name"],
            "genres": a["genres"],
            "id": a["id"],
        }
        for a in artists[:20]
    ]

    return {
        "time_range": time_range,
        "top_tracks": top_tracks_summary,
        "top_artists": top_artists_summary,
        "avg_audio_features": avg_features,
        "top_genres": top_genres,
        "taste_summary": taste_summary,
    }


# --- HTTP routes ---


async def handle_mcp(request: Request):
    await session_manager.handle_request(request.scope, request.receive, request._send)


async def healthcheck(request: Request):
    return JSONResponse({"status": "ok"})


async def on_startup():
    await session_manager.__aenter__()


async def on_shutdown():
    await session_manager.__aexit__(None, None, None)


app = Starlette(
    routes=[
        Route("/health", endpoint=healthcheck),
        Mount("/mcp", app=session_manager.handle_request),
    ],
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
