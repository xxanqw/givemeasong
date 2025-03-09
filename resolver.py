import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from ytmusicapi import YTMusic
import deezer
import soundcloud
import requests
import os
from dotenv import load_dotenv
import re

load_dotenv()

# Spotify API Setup
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID,
                                                                client_secret=SPOTIFY_CLIENT_SECRET))

# YouTube Music API Setup
ytmusic = YTMusic()

# Deezer API Setup
deezer_client = deezer.Client()

# SoundCloud API Setup
soundcloud_client = soundcloud.SoundCloud()

def resolve_spotify(url):
    """Extract song details from a Spotify URL."""
    track_id = url.split("/")[-1].split("?")[0]
    track = spotify.track(track_id)
    artists = [artist["name"] for artist in track["artists"]]
    return {
        "title": track["name"],
        "artists": artists,
        "album": track["album"]["name"],
        "cover_url": track["album"]["images"][0]["url"],
        "length": track["duration_ms"] / 1000,  # in seconds
        "track_id": track_id,
        "url": url
    }

def resolve_youtube(url):
    """Extract song details from a YouTube Music URL."""
    # Extract video ID from the URL, handling additional parameters
    video_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
    song = ytmusic.get_song(videoId=video_id)
    return {
        "title": song["videoDetails"]["title"],
        "artists": [song["videoDetails"]["author"]],
        "album": None,
        "cover_url": song["videoDetails"]["thumbnail"]["thumbnails"][-1]["url"],
        "length": song["videoDetails"]["lengthSeconds"],
        "video_id": video_id,
        "url": url
    }

def resolve_deezer(url):
    """Extract song details from a Deezer URL."""
    track_id = url.split("/")[-1]
    track = deezer_client.get_track(track_id)
    return {
        "title": track.title,
        "artists": [track.artist.name],
        "album": track.album.title,
        "cover_url": track.album.cover,
        "length": track.duration,
        "deezer_id": track_id,
        "url": url
    }

def resolve_soundcloud(url):
    """Extract song details from a SoundCloud URL."""
    try:
        resolved_track = soundcloud_client.resolve(url)
        if resolved_track:
            return {
                "title": resolved_track.title,
                "artists": [resolved_track.user.username],
                # SoundCloud doesn't have albums in the same way
                "cover_url": re.sub(r'-large\.(jpg|jpeg|png)', r'-t500x500.\1', resolved_track.artwork_url) if resolved_track.artwork_url else None,
                "length": resolved_track.duration / 1000,  # in seconds
                "soundcloud_id": resolved_track.id,
                "url": url
            }
        return None
    except requests.exceptions.HTTPError as e:
        print(f"SoundCloud API Error: {e}")
        return None

def search_spotify(title, artist):
    """Search for a song on Spotify."""
    try:
        results = spotify.search(q=f"track:{title} artist:{artist}", type="track", limit=1)
        if results["tracks"]["items"]:
            track = results["tracks"]["items"][0]
            artists = [artist["name"] for artist in track["artists"]]
            return {
                "title": track["name"],
                "artists": artists,
                "album": track["album"]["name"],
                "cover_url": track["album"]["images"][0]["url"],
                "length": track["duration_ms"] / 1000,  # in seconds
                "track_id": track["id"],
                "url": f"https://open.spotify.com/track/{track['id']}"
            }
        return None
    except Exception as e:
        print(f"Spotify API Error: {e}")
        return None

def search_youtube(title, artist):
    """Search for a song on YouTube Music."""
    try:
        results = ytmusic.search(f"{title} {artist}", filter="songs")
        if results:
            return {
                "title": results[0]["title"],
                "artists": [results[0]["artists"][0]["name"]],
                "album": results[0]["album"]["name"] if results[0]["album"] else None,
                "cover_url": results[0]["thumbnails"][0]["url"] if results[0]["thumbnails"] else None,
                "length": results[0]["duration"],
                "video_id": results[0]["videoId"],
                "url": f"https://music.youtube.com/watch?v={results[0]['videoId']}"
            }
        return None
    except Exception as e:
        print(f"YouTube Music API Error: {e}")
        return None

def search_deezer(title, artist):
    """Search for a song on Deezer."""
    try:
        results = deezer_client.search(f"{title} {artist}", 'track')
        if results:
            return {
                "title": results[0].title,
                "artists": results[0].artist.name,
                "album": results[0].album.title,
                "cover_url": results[0].album.cover,
                "length": results[0].duration,
                "deezer_id": results[0].id,
                "url": results[0].link
            }
        return None
    except Exception as e:
        print(f"Deezer API Error: {e}")
        return None

def search_soundcloud(title, artist):
    """Search for a song on SoundCloud."""
    try:
        tracks = soundcloud_client.search_tracks(query=f"{title} {artist}")
        first_track = next(tracks, None)
        if first_track:
            return {
                "title": first_track.title,
                "artists": first_track.user.username, 
                "album": None,  # SoundCloud doesn't have albums in the same way
                "cover_url": first_track.artwork_url,
                "length": first_track.duration / 1000,  # in seconds
                "soundcloud_id": first_track.id,
                "url": first_track.permalink_url
            }
        return None
    except requests.exceptions.HTTPError as e:
        print(f"SoundCloud API Error: {e}")
        return None
