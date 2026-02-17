import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Configures centralized logging for the application.
    Logs are sent to both the console and a rotating file.
    """
    # Navigate up to the backend directory to find logs folder
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    log_dir = os.path.join(base_dir, "logs")
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "app.log")
    
    # Create a logger
    logger = logging.getLogger("coincine")
    logger.setLevel(logging.INFO)

    # Prevent duplicating logs if setup is called multiple times
    if logger.handlers:
        return logger

    # Create formatters
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    # Rotating File Handler (1MB per file, keep last 5)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1*1024*1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    logger.info("Logging system initialized. Logs are saved to: %s", log_file)
    
    return logger

# Initialize on import
logger = setup_logging()
