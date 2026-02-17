from fastapi import APIRouter, HTTPException, Query
import random
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..models.movie import Movie
from ..scrapers.scraper import LetterboxdScraper
from ..core.logging import logger

router = APIRouter()

# In-memory storage
movies_db: List[Movie] = []
added_users_data = {} # Dictionary: {username: profile_picture}

# Shared driver for single operations
_shared_driver = None

def get_shared_driver():
    global _shared_driver
    if _shared_driver is None:
        scraper = LetterboxdScraper()
        _shared_driver = scraper._create_driver()
    return _shared_driver

@router.post("/add_user")
def add_user(username: str):
    print("eoeo")
    global added_users_data
    if username in added_users_data:
        raise HTTPException(status_code=400, detail=f"User {username} already added")
    
    with LetterboxdScraper(driver=get_shared_driver()) as scraper:
        profile_picture = scraper.get_profile_picture(username)
        added_users_data[username] = profile_picture
            
    return {
        "message": f"Added {username} to the list",
        "users": [{"username": u, "profile_picture": p} for u, p in added_users_data.items()]
    }

@router.post("/sync_all")
def sync_all_watchlists():
    global movies_db, added_users_data
    if not added_users_data:
        raise HTTPException(status_code=400, detail="No users added yet")
    
    movies_db = []
    total_movies = 0
    usernames = list(added_users_data.keys())
    
    def scrape_task(username):
        with LetterboxdScraper() as scraper:
            return {
                "username": username,
                "profile_picture": scraper.get_profile_picture(username),
                "watchlist": scraper.get_watchlist(username)
            }

    with ThreadPoolExecutor(max_workers=min(len(usernames), 5)) as executor:
        futures = {executor.submit(scrape_task, u): u for u in usernames}
        
        for future in as_completed(futures):
            try:
                data = future.result()
                username = data["username"]
                # Update profile picture cache in case it changed
                added_users_data[username] = data["profile_picture"]
                
                if data["watchlist"]:
                    for m_dict in data["watchlist"]:
                        if not any(m.letterboxd_url == m_dict["letterboxd_url"] for m in movies_db):
                            movies_db.append(Movie(**m_dict))
                            total_movies += 1
            except Exception as e:
                logger.error(f"Error syncing {futures[future]}: {e}")

    return {
        "message": f"Synced {len(usernames)} users in parallel",
        "total_movies": total_movies,
        "users": [{"username": u, "profile_picture": p} for u, p in added_users_data.items()]
    }

@router.get("/movies", response_model=List[Movie])
def get_movies():
    return movies_db

@router.post("/clear")
def clear_data():
    global movies_db, added_users_data
    movies_db = []
    added_users_data = {}
    return {"message": "All data cleared"}

@router.post("/remove")
def remove_user(username: str):
    global added_users_data
    if username in added_users_data:
        del added_users_data[username]
    return {
        "message": f"User {username} removed", 
        "users": [{"username": u, "profile_picture": p} for u, p in added_users_data.items()]
    }

@router.get("/roulette", response_model=List[Movie])
def get_roulette_candidates():
    """
    Returns all movies from in-memory list.
    """
    if not movies_db:
        raise HTTPException(status_code=404, detail="No movies in database. Sync first!")
    
    return movies_db

@router.get("/spin", response_model=Movie)
def spin_roulette():
    """
    Returns a single random movie.
    """
    if not movies_db:
        raise HTTPException(status_code=404, detail="No movies in database. Sync first!")
    
    return random.choice(movies_db)