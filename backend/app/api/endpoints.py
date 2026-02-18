from fastapi import APIRouter, HTTPException
from sqlmodel import select, func
import random
from typing import List, Optional
from ..models.models import Movie, User, UserMovieLink
from ..scrapers.scraper import LetterboxdScraper
from ..core.logging import logger
from ..core.database import get_session

import time # execution tests

router = APIRouter()

# Current session selection
session_users = {} # Dictionary: {username: profile_picture}
movies_db: List[Movie] = [] # Current session movies

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
    global session_users
    username = username.strip().lower() # Normalize
    if username in session_users:
        raise HTTPException(status_code=400, detail=f"User {username} already in current session")
    
    with next(get_session()) as db:
        # Check if user exists in DB
        statement = select(User).where(User.username == username)
        user = db.exec(statement).first()
        
        if user:
            logger.info(f"User {username} found in database.")
            session_users[username] = user.profile_picture
        else:
            logger.info(f"User {username} not found in DB. Scraping...")
            with LetterboxdScraper(driver=get_shared_driver()) as scraper:
                profile_picture = scraper.get_profile_picture(username)
                user = User(username=username, profile_picture=profile_picture)
                db.add(user)
                db.commit()
                db.refresh(user)
                session_users[username] = profile_picture
        
        # Build response with accurate frequent flag
        response_users = []
        for u_name in session_users:
            u_db = db.exec(select(User).where(User.username == u_name)).first()
            response_users.append({
                "username": u_name,
                "profile_picture": session_users[u_name],
                "frequent": u_db.frequent_user if u_db else False
            })
            
    return {
        "message": f"Added {username} to the list",
        "users": response_users
    }

@router.post("/sync_all")
def sync_all_watchlists():
    global movies_db, session_users
    if not session_users:
        raise HTTPException(status_code=400, detail="No users added yet")
    
    movies_db = []
    total_movies = 0
    usernames = list(session_users.keys())
    
    start_time = time.time()
    
    with next(get_session()) as db:
        for username in usernames:
            # Check if user has movies in DB
            statement = select(User).where(User.username == username)
            user = db.exec(statement).first()
            
            if user and user.movies:
                logger.info(f"Loading {len(user.movies)} movies for {username} from DB.")
                for movie in user.movies:
                    if not any(m.letterboxd_url == movie.letterboxd_url for m in movies_db):
                        movies_db.append(movie)
                        total_movies += 1
            else:
                logger.info(f"Scraping watchlist for {username}...")
                with LetterboxdScraper() as scraper:
                    watchlist_data = scraper.get_watchlist(username)
                    if watchlist_data:
                        # Save movies and link to user
                        current_user = db.exec(select(User).where(User.username == username)).one()
                        for m_dict in watchlist_data:
                            # Use existing movie or create new
                            movie = db.get(Movie, m_dict["letterboxd_url"])
                            if not movie:
                                movie = Movie(**m_dict)
                                db.add(movie)
                            
                            if movie not in current_user.movies:
                                current_user.movies.append(movie)
                            
                            if not any(m.letterboxd_url == m_dict["letterboxd_url"] for m in movies_db):
                                movies_db.append(movie)
                                total_movies += 1
                        db.commit()

    end_time = time.time()
    logger.info(f"DEBUG - Time taken to sync all watchlists: {end_time - start_time}")

    return {
        "message": f"Synced {len(usernames)} users",
        "total_movies": total_movies,
        "users": [{"username": u, "profile_picture": p} for u, p in session_users.items()]
    }

@router.get("/movies", response_model=List[Movie])
def get_movies():
    return movies_db

@router.post("/clear")
def clear_data():
    global movies_db, session_users
    movies_db = []
    session_users = {}
    return {"message": "Current session cleared"}

@router.post("/remove")
def remove_user(username: str):
    global session_users
    username = username.strip().lower()
    if username in session_users:
        del session_users[username]
    
    with next(get_session()) as db:
        response_users = []
        for u_name in session_users:
            u_db = db.exec(select(User).where(User.username == u_name)).first()
            response_users.append({
                "username": u_name,
                "profile_picture": session_users[u_name],
                "frequent": u_db.frequent_user if u_db else False
            })
            
    return {
        "message": f"User {username} removed from session", 
        "users": response_users
    }


# --- Persistent User Management ---

@router.get("/users/saved")
def get_saved_users():
    with next(get_session()) as db:
        users = db.exec(select(User).where(User.frequent_user == True)).all()
        return [{"username": u.username, "profile_picture": u.profile_picture} for u in users]

@router.post("/users/{username}/save_user")
def save_user(username: str):
    username = username.strip().lower()
    with next(get_session()) as db:
        user = db.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found in system")
        user.frequent_user = True
        db.add(user)
        db.commit()
    return {"message": f"User {username} saved as frequent"}

@router.delete("/users/{username}/save_user")
def unsave_user(username: str):
    username = username.strip().lower()
    with next(get_session()) as db:
        user = db.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.frequent_user = False
        db.add(user)
        db.commit()
    return {"message": f"User {username} removed from frequent"}

@router.post("/users/{username}/update_user")
def update_user_data(username: str):
    username = username.strip().lower()
    with next(get_session()) as db:
        user = db.exec(select(User).where(User.username == username)).first()
        if not user:
             raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"Force updating data for {username}...")
        with LetterboxdScraper() as scraper:
            # Update profile picture
            profile_picture = scraper.get_profile_picture(username)
            user.profile_picture = profile_picture
            
            # Update watchlist
            watchlist_data = scraper.get_watchlist(username)
            if watchlist_data:
                # Clear old associations (optional, but requested "update")
                user.movies = []
                for m_dict in watchlist_data:
                    movie = db.get(Movie, m_dict["letterboxd_url"])
                    if not movie:
                        movie = Movie(**m_dict)
                        db.add(movie)
                    user.movies.append(movie)
            
            db.add(user)
            db.commit()
            
    return {"message": f"Data updated for {username}"}

@router.get("/roulette", response_model=List[Movie])
def get_roulette_candidates(mode: str = "mix", max_movies: int = 20):
    """
    Returns movies for the roulette based on current session users.
    'mix' = Union of all watchlists.
    'match' = Intersection of all watchlists.
    """
    global session_users, movies_db
    
    if not session_users:
        raise HTTPException(status_code=400, detail="No users in session. Add users first!")

    usernames = [u.lower() for u in session_users.keys()]
    
    with next(get_session()) as db:
        if mode == "match":
            # Intersection: Movies that are present in ALL session users' watchlists.
            # We count distinct user_ids in the link table for each movie and compare with total users.
            user_count = len(usernames)
            
            # Subquery to get user IDs for safety
            user_ids_stmt = select(User.id).where(User.username.in_(usernames))
            user_ids = db.exec(user_ids_stmt).all()
            
            if not user_ids:
                 raise HTTPException(status_code=404, detail="Session users not found in DB")

            # Efficient SQL Intersection
            stmt = (
                select(Movie)
                .join(UserMovieLink)
                .where(UserMovieLink.user_id.in_(user_ids))
                .group_by(Movie.letterboxd_url)
                .having(func.count(UserMovieLink.user_id) == user_count)
            )
            roulette_movies = db.exec(stmt).all()
        else:
            # Mix (Union): Movies present in at least one of the session users' watchlists.
            stmt = (
                select(Movie)
                .join(UserMovieLink)
                .join(User)
                .where(User.username.in_(usernames))
                .distinct()
            )
            roulette_movies = db.exec(stmt).all()

    if not roulette_movies:
        return []

    # Shuffle and Limit
    random.shuffle(roulette_movies)
    if len(roulette_movies) > max_movies:
        roulette_movies = roulette_movies[:max_movies]
    
    # Update movies_db for /spin compatibility (though we should probably refactor /spin too)
    movies_db = roulette_movies

    return roulette_movies

@router.get("/spin", response_model=Movie)
def spin_roulette():
    """
    Returns a single random movie.
    """
    if not movies_db:
        raise HTTPException(status_code=404, detail="No movies in database. Sync first!")
    
    return random.choice(movies_db)