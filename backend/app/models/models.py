from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship

class UserMovieLink(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", primary_key=True)
    movie_id: Optional[str] = Field(default=None, foreign_key="movie.letterboxd_url", primary_key=True)

class Movie(SQLModel, table=True):
    __tablename__ = "movie"
    title: str = Field(index=True)
    letterboxd_url: str = Field(primary_key=True)
    poster_url: Optional[str] = None
    
    # Relationship to users
    users: List["User"] = Relationship(back_populates="movies", link_model=UserMovieLink)

class User(SQLModel, table=True):
    __tablename__ = "user"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    profile_picture: Optional[str] = None
    frequent_user: bool = Field(default=False)
    
    # Relationship to movies
    movies: List[Movie] = Relationship(back_populates="users", link_model=UserMovieLink)
