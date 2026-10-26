import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from ..core.logging import logger
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import undetected_chromedriver as uc
import random

import time # execution tests

class LetterboxdScraper:
    """
    A multi-purpose scraper for Letterboxd.
    Handles driver lifecycle and provides a clean interface for data extraction.
    """
    
    def __init__(self, driver=None, use_stealth=True):
        """
        Initialize with an optional existing driver.
        """
        self.driver = driver
        self.use_stealth = use_stealth
        self._is_external_driver = driver is not None

    def __enter__(self):
        if not self.driver:
            if self.use_stealth:
                self.driver = self._create_stealth_driver()
            else:
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
        options.add_argument("--headless=new") # Use new headless mode for better compatibility
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    @staticmethod
    def _create_stealth_driver():
        """
        Creates a new undetected Chrome driver instance.
        """
        logger.info("Creating a new STEALTH Chrome driver instance...")
        options = uc.ChromeOptions()
        # Headless mode can still be detected, but uc makes it harder.
        # Sometimes it's better to run headed if possible, but headless=True is common.
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = uc.Chrome(options=options)
        return driver

    def close(self):
        """
        Closes the driver if it was created by this instance.
        """
        if self.driver and not self._is_external_driver:
            try:
                self.driver.quit()
            except Exception:
                # Common on Windows with undetected-chromedriver
                pass
            self.driver = None
            logger.info("Chrome driver closed.")

    def get_profile_picture(self, username: str):
        """
        Public method to get a user's profile picture.
        """
        try:
            start_time = time.time()
            url = f"https://letterboxd.com/{username}/"
            self.driver.get(url)
            img_elem = self.driver.find_element(By.CSS_SELECTOR, "span.avatar img")
            end_time = time.time()
            logger.info(f"DEBUG - Time taken to get profile picture for {username}: {end_time - start_time}")
            return img_elem.get_attribute("src")
        except Exception as e:
            logger.warning(f"Failed to get profile picture for {username}: {e}")
            return None

    def get_watchlist_old(self, username: str):
        """
        Public method to scrape the full watchlist of a user.
        """
        movies = []
        try:
            start_time = time.time()
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
                time.sleep(random.uniform(2, 4))
                self._extract_movies_from_current_page(movies)
            end_time = time.time()
            logger.info(f"DEBUG - Time taken to scrape watchlist for {username}: {end_time - start_time}")
            logger.info(f"Successfully scraped {len(movies)} movies for {username}")
        except Exception as e:
            logger.error(f"Error scraping watchlist for {username}: {e}")
            
        return movies

    def get_watchlist(self, username: str):
        """
        Public method to scrape the full watchlist of a user.
        Returns None if the scrape failed or was incomplete, so callers never persist a partial watchlist.
        """
        movies = []
        try:
            start_time = time.time()
            url = f"https://letterboxd.com/{username}/watchlist/"
            self.driver.get(url)

            max_pages = self._get_max_pages()
            logger.info(f"Target user: {username} | Pages to scrape: {max_pages}")

            # Scrape first page
            time.sleep(random.uniform(2, 4))
            self._extract_movies_from_current_page(movies)

            if max_pages <= 1:
                return movies

            # Sequential scraping for now to ensure stability with uc
            for page in range(2, max_pages + 1):
                page_url = f"{url}page/{page}/"
                self.driver.get(page_url)
                time.sleep(random.uniform(2, 4))
                if self._extract_movies_from_current_page(movies) == 0:
                    # A listed page with no movies means we were blocked or the page failed to load
                    logger.error(f"Page {page} of {username}'s watchlist returned no movies. Discarding partial scrape.")
                    return None

            end_time = time.time()
            logger.info(f"DEBUG - Time taken to scrape watchlist for {username}: {end_time - start_time}")
            logger.info(f"Successfully scraped {len(movies)} movies for {username}")
        except Exception as e:
            logger.error(f"Error scraping watchlist for {username}: {e}")
            return None

        return movies

    def _get_max_pages(self):
        """
        Internal: Determines total number of pages in the watchlist.
        """
        try:
            # DEBUG OPTIONS
            #self.driver.save_screenshot("debug_page.png")
            #with open("debug_page.html", "w", encoding="utf-8") as f:
            #    f.write(self.driver.page_source)
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
        Returns the number of movies added.
        """
        added = 0
        elements = self.driver.find_elements(By.CSS_SELECTOR, "li.griditem")
        if not elements:
            logger.warning("No movies found. Does user have a watchlist?")
            return added
        for elem in elements:
            try:
                img_elem = elem.find_element(By.CSS_SELECTOR, "img")
                title = img_elem.get_attribute("alt")
                if title and title.startswith("Poster for "):
                    title = title.replace("Poster for ", "")
                
                poster_url = img_elem.get_attribute("src")
                link = elem.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                if not title or not link:
                    continue

                movies_list.append({
                    "title": title,
                    "letterboxd_url": link,
                    "poster_url": poster_url
                })
                added += 1
            except Exception:
                continue
        return added
