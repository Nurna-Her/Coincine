# 🟠​🟢​🔵​ Coincine
Spin your Letterboxd watchlist and find what to watch next.

## ​🎬 About

This is a **work in progress** and is only the first iteration of the app. Many details such as movie poster scraping don't work, and a lot of features are yet to be implemented, and the app is obvously not very curated (sorry). I built this app merely for fun and learning purposes, and I don't expect it to be used by anyone else.

## 🎥 Features
- **Watchlist Syncing**: Add Letterboxd users and sync their watchlists using web scraping.
- **Roulette Modes**:
  - **Mixing**: Combine all user watchlists into a single pool.
  - **Matching**: Only spin movies that everyone has in common.
- **Interaction Modes**: Select a single winner with one spin, or use elimination mode to narrow down choices.
- **Local Persistence**: Integrated database for faster loads of previously synced users.

Here is a snapshot on how the app works:

![coincine](https://github.com/user-attachments/assets/845a9e86-33c9-41a1-9962-e44dbfefc158)


## 🎞️ Tech Stack
- **Backend**: Python, FastAPI, SQLModel (SQLite), Selenium, undetected-chromedriver.
- **Frontend**: Vanilla HTML5, CSS3, JavaScript.

## ​📽️ Getting Started

First, clone the repo into your local machine.
Then install the required Python dependencies:
```bash
pip install -r requirements.txt
```

###  Running the Application
- **Windows**: Right-click `quicklaunch.ps1` and select "Run with PowerShell".
- **Linux**: Run `./quicklaunch.sh`.
- **Manual**:
  1. Start the backend:
     ```bash
     python -m uvicorn backend.app.main:app --reload
     ```
  2. Open http://localhost:8000/ in your browser (the backend serves the frontend).


## 📼 Usage
1. Enter a Letterboxd username and click **Add User**.
2. Click **Sync Up!** to fetch the watchlist data (this can take a while for new users).
3. Choose your modes and **SPIN**!


## 💿 Legally speaking

## About data scraping

The scraping of publicly available data may fall under Articles 3–4 of Directive 2019/790 (text and data mining exception for research and education) **as long as the data is public and the scraping is performed for non-commercial purposes**. All of the data used in this project is public, no private data is scraped or kept.

Letterboxd expressly prohibits scraping in its [Terms and Conditions](https://letterboxd.com/legal/terms-of-use/).
This project is **strictly academic and non-profit**; no commercial use of the code or the scraped data is allowed.

## License

Shield: [![CC BY-NC-SA 4.0][cc-by-nc-sa-shield]][cc-by-nc-sa]

This work is licensed under a
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License][cc-by-nc-sa].

[![CC BY-NC-SA 4.0][cc-by-nc-sa-image]][cc-by-nc-sa]

[cc-by-nc-sa]: http://creativecommons.org/licenses/by-nc-sa/4.0/
[cc-by-nc-sa-image]: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
[cc-by-nc-sa-shield]: https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg

