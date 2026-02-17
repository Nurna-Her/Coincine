from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global driver instance
_driver = None

def setup_driver():
    """
    Setup the global driver instance.
    """
    global _driver 
    
    if _driver is None:
        logger.info("Initializing global Chrome driver...")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        _driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        logger.info("Global Chrome driver initialized successfully")

    else:
        logger.info("Global Chrome driver already initialized")

    return True if _driver is not None else False

def get_driver():
    """
    Returns the global driver instance, creating it if necessary.
    Uses singleton pattern for driver reuse.
    """
    global _driver
    
    if _driver is None:
        logger.info("Driver instance not found. Initializing...")
        if not setup_driver():
            raise Exception("Failed to initialize driver")

    return _driver

def close_driver():
    """
    Closes the global driver if it exists.
    """
    global _driver
    
    if _driver is not None:
        logger.info("Closing global Chrome driver...")
        _driver.quit()
        _driver = None
        logger.info("Global Chrome driver closed")


def get_user_profile_picture(username: str):
    """
    Retrieves the profile picture URL of a user from Letterboxd.
    Uses the global driver instance.
    """
    driver = get_driver()
    try:
        url = f"https://letterboxd.com/{username}/" 
        driver.get(url)
        time.sleep(5)
        img_elem = driver.find_element(By.CSS_SELECTOR, "span.avatar img")
        return img_elem.get_attribute("src")
    except Exception as e:  
        logger.warning(f"Failed to get user profile picture: {e}")
        return None


def watchlist_callback(driver, movies):
    """
    Callback function to extract movies from the current page.
    """
    elements = driver.find_elements(By.CSS_SELECTOR, "li.griditem")

    for elem in elements:
        try:
            img_elem = elem.find_element(By.CSS_SELECTOR, "img")
            title = img_elem.get_attribute("alt")
            if title and title.startswith("Poster for "):
                title = title.replace("Poster for ", "")
        
            poster_url = img_elem.get_attribute("src")
        
            link_elem = elem.find_element(By.CSS_SELECTOR, "a")
            link = link_elem.get_attribute("href")
        
            movies.append({
                "title": title,
                "letterboxd_url": link,
                "poster_url": poster_url
            })
        except Exception as e:
            logger.warning(f"Failed to parse a movie element: {e}")
            continue

def get_watchlist(driver, username: str):
    """
    Scrapes the watchlist of a given Letterboxd user.
    """
    movies = []

    try:
        url = f"https://letterboxd.com/{username}/watchlist/"
        driver.get(url)
        # get pagination of watchlist
        try:
            pagination = driver.find_element(By.CSS_SELECTOR, "div.paginate-pages")
            page_items = pagination.find_elements(By.CSS_SELECTOR, "li.paginate-page")
    
            if page_items:
                last_page_text = page_items[-1].text
                max_pages = int(last_page_text)
        except Exception:
            max_pages = 1
        time.sleep(5)
        
        watchlist_callback(driver, movies) # first page
        for current_page in range(2, max_pages + 1):
            url = f"https://letterboxd.com/{username}/watchlist/page/{current_page}/"
            driver.get(url)
            time.sleep(5)
            watchlist_callback(driver, movies)
                
        logger.info(f"Found {len(movies)} movies.")
        
        if len(movies) == 0:
            logger.warning("No movies found. Dumping page source to debug_failed_scrape.html")
            with open("debug_failed_scrape.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
                
        return movies
        
    except Exception as e:
        logger.error(f"Error scraping watchlist: {e}")
        return []


def scrape_user(username: str):
    logger.info(f"Starting scrape for user: {username}")
    
    driver = get_driver()

    watchlist = get_watchlist(driver, username)
    
    return {
        "username": username,
        "watchlist": watchlist
    }

if __name__ == "__main__":
    # Test run
    data = scrape_user("JohnDoe")
    print(data)
