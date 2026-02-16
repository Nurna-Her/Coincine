from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import random
from typing import List

from .models import Movie
from .scraper import scrape_user

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
users_data: dict = {}  # {username: {"profile_picture": url, "movies": [...]}}

@app.post("/api/sync")
def sync_watchlist(username: str):
    """
    Scrapes the user's watchlist and profile picture, adds to the in-memory list.
    """
    global movies_db, users_data
    
    if username in users_data:
        raise HTTPException(status_code=400, detail=f"User {username} already added")
    
    # Scrape user data (profile picture + watchlist)
    user_data = scrape_user(username)
    
    if not user_data or not user_data.get("watchlist"):
        raise HTTPException(status_code=404, detail="No movies found or user does not exist")

    # Store user data
    users_data[username] = {
        "profile_picture": user_data.get("profile_picture"),
        "movies": user_data["watchlist"]
    }
    
    # Append movies to existing list (don't clear)
    new_movies_count = 0
    for movie_dict in user_data["watchlist"]:
        # Check if movie already exists (by letterboxd_url)
        if not any(m.letterboxd_url == movie_dict["letterboxd_url"] for m in movies_db):
            movie = Movie(
                title=movie_dict["title"],
                letterboxd_url=movie_dict["letterboxd_url"],
                poster_url=movie_dict.get("poster_url")
            )
            movies_db.append(movie)
            new_movies_count += 1
    
    return {
        "message": f"Added {new_movies_count} new movies from {username}",
        "total_movies": len(movies_db),
        "users": [{"username": u, "profile_picture": users_data[u]["profile_picture"]} for u in users_data.keys()]
    }

@app.post("/api/clear")
def clear_watchlists():
    """
    Clears all watchlists and users.
    """
    global movies_db, users_data
    movies_db = []
    users_data = {}
    return {"message": "Cleared all watchlists"}

@app.post("/api/remove")
def remove_user(username: str):
    """
    Removes a specific user and re-syncs movies from remaining users.
    """
    global movies_db, users_data
    
    if username not in users_data:
        raise HTTPException(status_code=404, detail=f"User {username} not found")
    
    # Remove user from dict
    del users_data[username]
    
    # Rebuild movie list from remaining users
    movies_db = []
    for user, data in users_data.items():
        for movie_dict in data["movies"]:
            # Check if movie already exists
            if not any(m.letterboxd_url == movie_dict["letterboxd_url"] for m in movies_db):
                movie = Movie(
                    title=movie_dict["title"],
                    letterboxd_url=movie_dict["letterboxd_url"],
                    poster_url=movie_dict.get("poster_url")
                )
                movies_db.append(movie)
    
    return {
        "message": f"Removed {username}",
        "total_movies": len(movies_db),
        "users": [{"username": u, "profile_picture": users_data[u]["profile_picture"]} for u in users_data.keys()]
    }

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
