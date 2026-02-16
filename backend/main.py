from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import random
from typing import List

from .models import Movie
from .scraper import get_watchlist

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
movies_db: List[Movie] = []

@app.post("/api/sync")
def sync_watchlist(username: str):
    """
    Scrapes the user's watchlist and updates the in-memory list.
    """
    global movies_db
    movies_data = get_watchlist(username)
    
    if not movies_data:
        raise HTTPException(status_code=404, detail="No movies found or user does not exist")

    # Clear existing list and update
    movies_db = []
    
    for movie_dict in movies_data:
        movie = Movie(
            title=movie_dict["title"],
            letterboxd_url=movie_dict["letterboxd_url"],
            poster_url=movie_dict.get("poster_url")
        )
        movies_db.append(movie)
    
    return {"message": f"Synced {len(movies_data)} movies for {username}"}

@app.get("/api/roulette", response_model=List[Movie])
def get_roulette_candidates():
    """
    Returns all movies from in-memory list.
    """
    if not movies_db:
        raise HTTPException(status_code=404, detail="No movies in database. Sync first!")
    
    return movies_db

@app.get("/api/spin", response_model=Movie)
def spin_roulette():
    """
    Returns a single random movie.
    """
    if not movies_db:
        raise HTTPException(status_code=404, detail="No movies in database. Sync first!")
    
    return random.choice(movies_db)
