import sys
from scraper import get_watchlist

def test_watchlist(username):
    print(f"\n--- Testing Watchlist for user: {username} ---")
    movies = get_watchlist(username)
    print(f"Found {len(movies)} movies.")
    if movies:
        print("First 3 movies found:")
        for movie in movies[:3]:
            print(f" - {movie['title']} ({movie['letterboxd_url']})")
    else:
        print("No movies found or error occurred.")

if __name__ == "__main__":
    users_to_test = ["JohnDoe"] # Example users
    
    if len(sys.argv) > 1:
        users_to_test = sys.argv[1:]
        
    for user in users_to_test:
        test_watchlist(user)
