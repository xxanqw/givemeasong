from fastapi import FastAPI, Depends, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware  # Add this import
from sqlalchemy.orm import Session
from uuid import uuid4
from database import SessionLocal, save_song, get_song, search_song
from resolver import resolve_spotify, resolve_youtube, resolve_soundcloud, resolve_deezer, search_spotify, search_youtube, search_deezer, search_soundcloud
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with your Next.js app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Change OpenAPI URL to /gmas/openapi.json
app.openapi_url = "/gmas/openapi.json"

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="GiveMeASong API",
        version="2-beta",
        description="Просте та швидке API для Пінчани, яке знаходить пісню по посиланню на всіх (поки що зроблених) платформах.",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/resolve")
async def resolve_music_url(request: Request, url: str = Query(...), db: Session = Depends(get_db)):
    """Find the song and update it with new platform data if needed."""
    if "spotify.com" not in url and "music.youtube.com" not in url and "deezer.com" not in url and "soundcloud.com" not in url:
        return JSONResponse({"error": "Invalid URL"}, status_code=400)

    song_data = None
    try:
        if "spotify.com" in url:
            song_data = resolve_spotify(url)
        elif "music.youtube.com" in url:
            song_data = resolve_youtube(url)
        elif "deezer.com" in url:
            song_data = resolve_deezer(url)
        elif "soundcloud.com" in url:
            song_data = resolve_soundcloud(url)
        else:
            return JSONResponse({"error": "Unsupported platform"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    if song_data is None:
        return JSONResponse({"error": "Could not resolve song"}, status_code=500)

    title = song_data["title"]
    artists = song_data["artists"]
    artist = ", ".join(artists)

    # Try to find the song in the database
    existing_song = search_song(db, title, artist)

    if existing_song:
        song_id = existing_song.id
    else:
        # Generate a unique ID for the song
        song_id = str(uuid4())

    # Get platform links
    spotify_data = search_spotify(title, artist)
    youtube_music_data = search_youtube(title, artist)
    deezer_data = search_deezer(title, artist)
    soundcloud_data = search_soundcloud(title, artist)

    new_platforms = {
        "spotify": spotify_data,
        "youtube_music": youtube_music_data,
        "deezer": deezer_data,
        "soundcloud": soundcloud_data,
    }
    new_platforms = {k: v for k, v in new_platforms.items() if v}

    song_data = {
        "id": song_id,
        "title": title,
        "artist": artist,
        "platforms": new_platforms,
        "cover_url": song_data.get("cover_url")
    }

    # Save song
    save_song(db, song_data)

    return song_data

@app.get("/song/{song_id}")
def get_song_details(song_id: str, request: Request, db: Session = Depends(get_db)):
    """Return song details as JSON and update with any newly available platforms."""
    song = get_song(db, song_id)
    if not song:
        return JSONResponse({"error": "Song not found"}, status_code=404)
    
    # Check for newly available platforms
    spotify_data = search_spotify(song.title, song.artist)
    youtube_music_data = search_youtube(song.title, song.artist)
    deezer_data = search_deezer(song.title, song.artist)
    soundcloud_data = search_soundcloud(song.title, song.artist)

    new_platforms = {
        "spotify": spotify_data,
        "youtube_music": youtube_music_data,
        "deezer": deezer_data,
        "soundcloud": soundcloud_data,
    }
    existing_platforms = song.platforms or {}
    new_platforms = {k: v for k, v in new_platforms.items() if v and k not in existing_platforms}

    if new_platforms:
        # Update existing song with new platforms
        song.platforms = {**existing_platforms, **new_platforms}
        save_song(db, song)

    # Return song data formatted for the frontend
    return {
        "id": song.id,
        "title": song.title,
        "artist": song.artist,
        "cover_url": getattr(song, "cover_url", None),
        "platforms": song.platforms
    }
