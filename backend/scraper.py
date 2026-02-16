from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def callback(driver, movies):
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

def get_watchlist(username: str):
    """
    Scrapes the watchlist of a given Letterboxd user.
    """
    logger.info(f"Starting scrape for user: {username}")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

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
        
        callback(driver, movies) # first page
        for current_page in range(2, max_pages + 1):
            url = f"https://letterboxd.com/{username}/watchlist/page/{current_page}/"
            driver.get(url)
            time.sleep(5)
            callback(driver, movies)
                
        logger.info(f"Found {len(movies)} movies.")
        
        if len(movies) == 0:
            logger.warning("No movies found. Dumping page source to debug_failed_scrape.html")
            with open("debug_failed_scrape.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
                
        return movies
        
    except Exception as e:
        logger.error(f"Error scraping watchlist: {e}")
        return []
    finally:
        driver.quit()

if __name__ == "__main__":
    # Test run
    data = get_watchlist("JohnDoe")
    print(data)
