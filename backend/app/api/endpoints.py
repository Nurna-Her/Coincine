from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select, func
from sqlalchemy.exc import IntegrityError
import random
import re
import threading
from typing import List, Literal
from ..models.models import Movie, User, UserMovieLink
from ..scrapers.scraper import LetterboxdScraper
from ..core.logging import logger
from ..core.database import get_session

import time # execution tests

router = APIRouter()

# Current session selection
session_users = {} # Dictionary: {username: profile_picture}
movies_db: List[Movie] = [] # Current session movies
_state_lock = threading.Lock() # Guards session_users and movies_db

# Shared driver for single operations
_shared_driver = None
_driver_lock = threading.Lock() # Selenium drivers are not thread-safe: one request at a time

# Serializes the scrapes that write watchlists, so concurrent syncs don't insert the same movies twice
_sync_lock = threading.Lock()

# Letterboxd usernames only contain letters, numbers and underscores
USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{1,50}$")

def normalize_username(username: str) -> str:
    username = username.strip().lower()
    if not USERNAME_PATTERN.match(username):
        raise HTTPException(status_code=400, detail="Invalid Letterboxd username")
    return username

def get_shared_driver():
    """
    Returns the shared driver, recreating it if its browser died. Caller must hold _driver_lock.
    """
    global _shared_driver
    if _shared_driver is not None:
        try:
            _shared_driver.current_url
        except Exception:
            logger.warning("Shared driver is unresponsive. Recreating it...")
            close_shared_driver()
    if _shared_driver is None:
        _shared_driver = LetterboxdScraper._create_driver()
    return _shared_driver

def close_shared_driver():
    global _shared_driver
    if _shared_driver is not None:
        try:
            _shared_driver.quit()
        except Exception:
            pass
        _shared_driver = None

def build_session_users_response(db):
    with _state_lock:
        current_users = list(session_users.items())
    usernames = [u_name for u_name, _ in current_users]
    frequent_by_name = {
        u.username: u.frequent_user
        for u in db.exec(select(User).where(User.username.in_(usernames))).all()
    }
    return [
        {
            "username": u_name,
            "profile_picture": picture,
            "frequent": frequent_by_name.get(u_name, False)
        }
        for u_name, picture in current_users
    ]

@router.post("/add_user")
def add_user(username: str):
    username = normalize_username(username)
    with _state_lock:
        if username in session_users:
            raise HTTPException(status_code=400, detail=f"User {username} already in current session")

    with next(get_session()) as db:
        # Check if user exists in DB
        statement = select(User).where(User.username == username)
        user = db.exec(statement).first()

        if user:
            logger.info(f"User {username} found in database.")
        else:
            logger.info(f"User {username} not found in DB. Scraping...")
            with _driver_lock:
                with LetterboxdScraper(driver=get_shared_driver()) as scraper:
                    profile_picture = scraper.get_profile_picture(username)
            user = User(username=username, profile_picture=profile_picture)
            db.add(user)
            try:
                db.commit()
            except IntegrityError:
                # Another request created the same user in the meantime
                db.rollback()
                user = db.exec(statement).one()

        with _state_lock:
            session_users[username] = user.profile_picture

        response_users = build_session_users_response(db)

    return {
        "message": f"Added {username} to the list",
        "users": response_users
    }

@router.post("/sync_all")
def sync_all_watchlists():
    global movies_db
    with _state_lock:
        if not session_users:
            raise HTTPException(status_code=400, detail="No users added yet")
        usernames = list(session_users.keys())

    synced_movies = []
    seen_urls = set()

    start_time = time.time()

    with _sync_lock, next(get_session()) as db:
        for username in usernames:
            # Check if user has movies in DB
            statement = select(User).where(User.username == username)
            user = db.exec(statement).first()
            if not user:
                logger.warning(f"User {username} is in session but not in DB. Skipping.")
                continue

            if user.movies:
                logger.info(f"Loading {len(user.movies)} movies for {username} from DB.")
                user_movies = user.movies
            else:
                logger.info(f"Scraping watchlist for {username}...")
                with LetterboxdScraper() as scraper:
                    watchlist_data = scraper.get_watchlist(username)
                if not watchlist_data:
                    continue
                # Save movies and link to user
                user_movies = []
                for m_dict in watchlist_data:
                    # Use existing movie or create new
                    movie = db.get(Movie, m_dict["letterboxd_url"])
                    if not movie:
                        movie = Movie(**m_dict)
                        db.add(movie)
                    user_movies.append(movie)
                user.movies = list({m.letterboxd_url: m for m in user_movies}.values())
                db.commit()

            for movie in user_movies:
                if movie.letterboxd_url not in seen_urls:
                    seen_urls.add(movie.letterboxd_url)
                    synced_movies.append(movie)

    end_time = time.time()
    logger.info(f"DEBUG - Time taken to sync all watchlists: {end_time - start_time}")

    with _state_lock:
        movies_db = synced_movies
        current_users = list(session_users.items())

    return {
        "message": f"Synced {len(usernames)} users",
        "total_movies": len(synced_movies),
        "users": [{"username": u, "profile_picture": p} for u, p in current_users]
    }

@router.get("/movies", response_model=List[Movie])
def get_movies():
    return movies_db

@router.post("/clear")
def clear_data():
    global movies_db, session_users
    with _state_lock:
        movies_db = []
        session_users = {}
    return {"message": "Current session cleared"}

@router.post("/remove")
def remove_user(username: str):
    global movies_db
    username = normalize_username(username)
    with _state_lock:
        session_users.pop(username, None)
        # The pool may contain this user's movies: force a rebuild through /roulette
        movies_db = []

    with next(get_session()) as db:
        response_users = build_session_users_response(db)

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
    username = normalize_username(username)
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
    username = normalize_username(username)
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
    username = normalize_username(username)
    with _sync_lock, next(get_session()) as db:
        user = db.exec(select(User).where(User.username == username)).first()
        if not user:
             raise HTTPException(status_code=404, detail="User not found")

        logger.info(f"Force updating data for {username}...")
        with LetterboxdScraper() as scraper:
            # Update profile picture, keeping the stored one if scraping fails
            profile_picture = scraper.get_profile_picture(username)
            if profile_picture:
                user.profile_picture = profile_picture

            # Update watchlist only with a complete scrape, so a failure never drops stored movies
            watchlist_data = scraper.get_watchlist(username)

        if watchlist_data:
            new_movies = {}
            for m_dict in watchlist_data:
                movie = db.get(Movie, m_dict["letterboxd_url"])
                if not movie:
                    movie = Movie(**m_dict)
                    db.add(movie)
                new_movies[movie.letterboxd_url] = movie
            user.movies = list(new_movies.values())

        db.add(user)
        db.commit()

        if profile_picture:
            with _state_lock:
                if username in session_users:
                    session_users[username] = profile_picture

    if watchlist_data is None:
        raise HTTPException(status_code=502, detail=f"Could not scrape the full watchlist of {username}. Stored movies were kept.")
    if not watchlist_data:
        return {"message": f"No movies found for {username}. Stored movies were kept."}

    return {"message": f"Data updated for {username}"}

@router.get("/roulette", response_model=List[Movie])
def get_roulette_candidates(mode: Literal["mix", "match"] = "mix", max_movies: int = Query(20, ge=1)):
    """
    Returns movies for the roulette based on current session users.
    'mix' = Union of all watchlists.
    'match' = Intersection of all watchlists.
    """
    global movies_db

    with _state_lock:
        if not session_users:
            movies_db = []
            raise HTTPException(status_code=400, detail="No users in session. Add users first!")
        usernames = list(session_users.keys())

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

    # Shuffle and Limit
    roulette_movies = list(roulette_movies)
    random.shuffle(roulette_movies)
    roulette_movies = roulette_movies[:max_movies]

    # Update movies_db for /spin compatibility (though we should probably refactor /spin too)
    with _state_lock:
        movies_db = roulette_movies

    return roulette_movies

@router.get("/spin", response_model=Movie)
def spin_roulette():
    """
    Returns a single random movie.
    """
    current_movies = movies_db
    if not current_movies:
        raise HTTPException(status_code=404, detail="No movies in database. Sync first!")

    return random.choice(current_movies)
