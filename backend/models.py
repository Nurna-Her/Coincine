from typing import Optional
from sqlmodel import Field, SQLModel

class Movie(SQLModel):
    title: str
    letterboxd_url: str
    poster_url: Optional[str] = None

