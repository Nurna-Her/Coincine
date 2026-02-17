import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from ..core.logging import logger

class LetterboxdScraper:
    """
    A professional scraper for Letterboxd.
    Handles driver lifecycle and provides a clean interface for movie data extraction.
    """
    
    def __init__(self, driver=None):
        """
        Initialize with an optional existing driver.
        """
        self.driver = driver
        self._is_external_driver = driver is not None

    def __enter__(self):
        if not self.driver:
            self.driver = self._create_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._is_external_driver:
            self.close()

    @staticmethod
    def _create_driver():
        """
        Creates a new Chrome driver with optimized settings.
        """
        logger.info("Creating a new Chrome driver instance...")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def close(self):
        """
        Closes the driver if it was created by this instance.
        """
        if self.driver and not self._is_external_driver:
            self.driver.quit()
            self.driver = None
            logger.info("Chrome driver closed.")

    def get_profile_picture(self, username: str):
        """
        Public method to get a user's profile picture.
        """
        try:
            url = f"https://letterboxd.com/{username}/"
            self.driver.get(url)
            time.sleep(2)
            img_elem = self.driver.find_element(By.CSS_SELECTOR, "span.avatar img")
            return img_elem.get_attribute("src")
        except Exception as e:
            logger.warning(f"Failed to get profile picture for {username}: {e}")
            return None

    def get_watchlist(self, username: str):
        """
        Public method to scrape the full watchlist of a user.
        """
        movies = []
        try:
            url = f"https://letterboxd.com/{username}/watchlist/"
            self.driver.get(url)
            
            max_pages = self._get_max_pages()
            logger.info(f"Target user: {username} | Pages to scrape: {max_pages}")
            
            # Scrape first page
            time.sleep(2)
            self._extract_movies_from_current_page(movies)
            
            # Scrape subsequent pages
            for page in range(2, max_pages + 1):
                page_url = f"{url}page/{page}/"
                self.driver.get(page_url)
                time.sleep(2)
                self._extract_movies_from_current_page(movies)
                
            logger.info(f"Successfully scraped {len(movies)} movies for {username}")
        except Exception as e:
            logger.error(f"Error scraping watchlist for {username}: {e}")
            
        return movies

    def _get_max_pages(self):
        """
        Internal: Determines total number of pages in the watchlist.
        """
        try:
            pagination = self.driver.find_element(By.CSS_SELECTOR, "div.paginate-pages")
            page_items = pagination.find_elements(By.CSS_SELECTOR, "li.paginate-page")
            if page_items:
                return int(page_items[-1].text)
        except Exception:
            pass
        return 1

    def _extract_movies_from_current_page(self, movies_list):
        """
        Internal: Parses movie elements from the current page.
        """
        elements = self.driver.find_elements(By.CSS_SELECTOR, "li.griditem")
        for elem in elements:
            try:
                img_elem = elem.find_element(By.CSS_SELECTOR, "img")
                title = img_elem.get_attribute("alt")
                if title and title.startswith("Poster for "):
                    title = title.replace("Poster for ", "")
                
                poster_url = img_elem.get_attribute("src")
                link = elem.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                
                movies_list.append({
                    "title": title,
                    "letterboxd_url": link,
                    "poster_url": poster_url
                })
            except Exception:
                continue
