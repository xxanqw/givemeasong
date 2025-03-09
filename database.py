from sqlalchemy import create_engine, Column, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

DATABASE_URL = "sqlite:///./songs.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Song(Base):
    __tablename__ = "songs"

    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    artist = Column(String)
    platforms = Column(JSON)  # Stores available links
    cover_url = Column(String, nullable=True)


Base.metadata.create_all(bind=engine)


def save_song(db: Session, song_data):
    """Save or update song details in the database."""
    song = db.query(Song).filter(Song.id == song_data['id']).first()

    if song:
        # Merge new platforms with existing ones
        existing_platforms = song.platforms or {}
        updated_platforms = {**existing_platforms, **song_data['platforms']}
        song.platforms = updated_platforms
        song.title = song_data['title']
        song.artist = song_data['artist']
        song.cover_url = song_data.get('cover_url')
    else:
        song = Song(
            id=song_data['id'], 
            title=song_data['title'], 
            artist=song_data['artist'], 
            platforms=song_data['platforms'],
            cover_url=song_data.get('cover_url')
        )
        db.add(song)

    db.commit()
    


def get_song(db: Session, song_id):
    """Fetch song details from the database by ID."""
    song = db.query(Song).filter(Song.id == song_id).first()
    return song

def search_song(db: Session, title: str, artist: str):
    """Search for a song in the database by title and artist."""
    song = db.query(Song).filter(Song.title == title, Song.artist == artist).first()
    return song
