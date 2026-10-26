from sqlmodel import create_engine, SQLModel, Session
import os

# SQLite database file, resolved from the repo root so it doesn't depend on the working directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATABASE_DIR = os.path.join(BASE_DIR, "users", "data")
DATABASE_FILE = "coincine.db"
os.makedirs(DATABASE_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DATABASE_DIR, DATABASE_FILE)}"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def create_db_and_tables():
    # Import all models to ensure they are registered with SQLModel.metadata
    from ..models.models import User, UserMovieLink, Movie
    SQLModel.metadata.create_all(engine)

def get_session():
    # Keep loaded attributes after commit: movies are cached in memory and served after the session closes
    with Session(engine, expire_on_commit=False) as session:
        yield session
