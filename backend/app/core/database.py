from sqlmodel import create_engine, SQLModel, Session
import os

# SQLite database file
DATABASE_FILE = "coincine.db"
DATABASE_URL = f"sqlite:///./users/data/{DATABASE_FILE}"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def create_db_and_tables():
    # Import all models to ensure they are registered with SQLModel.metadata
    from ..models.models import User, UserMovieLink, Movie
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
