from typing import Optional
from sqlmodel import SQLModel, Field

class Movie(SQLModel, table=False):
    title: str = Field(index=True)
    letterboxd_url: str = Field(primary_key=True)
    poster_url: Optional[str] = None
