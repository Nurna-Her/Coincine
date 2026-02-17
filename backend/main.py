from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import random
from typing import List

from .models import Movie
from .scraper import scrape_user, get_user_profile_picture, get_driver, close_driver, setup_driver

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """
    Initialize the global Chrome driver on startup.
    """
    # Initialize driver by calling get_driver()
    setup_driver()

@app.on_event("shutdown")
async def shutdown_event():
    """
    Close the global Chrome driver on shutdown.
    """
    close_driver()

# In-memory storage
movies_db: List[Movie] = []
added_usernames: List[str] = []  # Just usernames, not scraped yet

@app.post("/api/add_user")
def add_user(username: str):
    """
    Adds a username to the list without scraping.
    """
    global added_usernames
    
    if username in added_usernames:
        raise HTTPException(status_code=400, detail=f"User {username} already added")
    
    added_usernames.append(username)
    
    return {
        "message": f"Added {username} to the list",
        "users": [{"username": u, "profile_picture": get_user_profile_picture(username)} for u in added_usernames]
    }

@app.post("/api/sync_all")
def sync_all_watchlists():
    """
    Scrapes all added users' watchlists and profile pictures.
    """
    global movies_db, added_usernames
    
    if not added_usernames:
        raise HTTPException(status_code=400, detail="No users added yet")
    
    movies_db = []  # Clear existing movies
    users_data = {}  # Temporary storage for scraped data
    total_movies = 0
    
    for username in added_usernames:
        try:
            # Scrape user data (profile picture + watchlist)
            user_data = scrape_user(username)
            
            if user_data and user_data.get("watchlist"):
                users_data[username] = {
                    "profile_picture": user_data.get("profile_picture"),
                    "movies": user_data["watchlist"]
                }
                
                # Add movies to database
                for movie_dict in user_data["watchlist"]:
                    # Check if movie already exists (by letterboxd_url)
                    if not any(m.letterboxd_url == movie_dict["letterboxd_url"] for m in movies_db):
                        movie = Movie(
                            title=movie_dict["title"],
                            letterboxd_url=movie_dict["letterboxd_url"],
                            poster_url=movie_dict.get("poster_url")
                        )
                        movies_db.append(movie)
                        total_movies += 1
        except Exception as e:
            print(f"Error scraping {username}: {e}")
            continue
    
    return {
        "message": f"Synced {len(added_usernames)} users, loaded {total_movies} unique movies",
        "total_movies": total_movies,
        "users": [{"username": u, "profile_picture": users_data.get(u, {}).get("profile_picture")} for u in added_usernames]
    }

@app.post("/api/clear")
def clear_watchlists():
    """
    Clears all watchlists and users.
    """
    global movies_db, added_usernames
    movies_db = []
    added_usernames = []
    return {"message": "Cleared all watchlists"}

@app.post("/api/remove")
def remove_user(username: str):
    """
    Removes a specific user from the added list.
    """
    global added_usernames
    
    if username not in added_usernames:
        raise HTTPException(status_code=404, detail=f"User {username} not found")
    
    # Remove user from list
    added_usernames.remove(username)
    
    return {
        "message": f"Removed {username}",
        "users": [{"username": u, "profile_picture": None} for u in added_usernames]
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
