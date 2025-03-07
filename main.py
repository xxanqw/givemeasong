from fastapi import FastAPI, Depends, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session
from uuid import uuid4
from database import SessionLocal, save_song, get_song, search_song
from resolver import resolve_spotify, resolve_youtube, resolve_soundcloud, resolve_deezer,search_spotify, search_youtube, search_deezer, search_soundcloud
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

app = FastAPI()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="GiveMeASong API",
        version="1-beta",
        description="Просте та швидке API для Пінчани, яке знаходить пісню по посиланню на всіх (поки що зроблених) платформах.",
        routes=app.routes,
        
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Set up templates and static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Set up templates and static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Render the homepage with a search form."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/resolve", response_class=HTMLResponse, responses={
    200: {
        "content": {"application/json": {}}
    },
    400: {
        "content": {"application/json": {}}
    },
    500: {
        "content": {"application/json": {}}
    }
})
async def resolve_music_url(request: Request, url: str = Query(...), db: Session = Depends(get_db)):
    """Find the song and update it with new platform data if needed."""
    if "spotify.com" not in url and "music.youtube.com" not in url and "deezer.com" not in url and "soundcloud.com" not in url:
        if request.headers.get("accept") == "application/json":
            return JSONResponse({"error": "Invalid URL"}, status_code=400)
        return templates.TemplateResponse("index.html", {"request": request, "error": "Invalid URL", "song_data": None})

    song_data = None
    try:
        if "spotify.com" in url:
            song_data = resolve_spotify(url)
        elif "music.youtube.com" in url:
            song_data = resolve_youtube(url)
            print(song_data)
        elif "deezer.com" in url:
            song_data = resolve_deezer(url)
        elif "soundcloud.com" in url:
            song_data = resolve_soundcloud(url)
        else:
            if request.headers.get("accept") == "application/json":
                return JSONResponse({"error": "Unsupported platform"}, status_code=400)
            return templates.TemplateResponse("index.html", {"request": request, "error": "Unsupported platform", "song_data": None})
    except Exception as e:
        if request.headers.get("accept") == "application/json":
            return JSONResponse({"error": str(e)}, status_code=500)
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e), "song_data": None})

    if song_data is None:
        return RedirectResponse(url="/", status_code=303)

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

    if request.headers.get("accept") == "application/json":
        return JSONResponse(song_data, status_code=200)

    return RedirectResponse(url=f"/song/{song_id}", status_code=303)

@app.get("/song/{song_id}", response_class=HTMLResponse)
def get_song_details(song_id: str, request: Request, _db: Session = Depends(get_db)):
    """Display song details and update with any newly available platforms."""
    song = get_song(song_id) # Access the database to get the song
    if not song:
        return HTMLResponse("<h1>Song not found</h1>", status_code=404)
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
    new_platforms = {k: v for k, v in new_platforms.items() if v and k not in (song.platforms or {})}

    if new_platforms:
        # Update existing song with new platforms
        song.platforms = {**(song.platforms or {}), **new_platforms}
        _db.commit()

    return templates.TemplateResponse(
        "song.html",
        {
            "request": request,
            "song": song,
            "platforms": song.platforms,
        },
    )