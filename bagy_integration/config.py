"""
Configuration settings for the Bagy to GestãoClick synchronization tool.
"""
import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# API Keys and Credentials
BAGY_API_KEY = os.getenv("BAGY_API_KEY")
GESTAOCLICK_API_KEY = os.getenv("GESTAOCLICK_API_KEY")
GESTAOCLICK_EMAIL = os.getenv("GESTAOCLICK_EMAIL")

# API Base URLs
BAGY_BASE_URL = os.getenv("BAGY_BASE_URL", "https://api.dooca.store")
GESTAOCLICK_BASE_URL = os.getenv("GESTAOCLICK_BASE_URL", "https://api.beteltecnologia.com")

# Sync settings
SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))  # Default to hourly sync
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "30"))

# Data storage settings
STORAGE_DIR = os.getenv("STORAGE_DIR", "./data")
SYNC_HISTORY_FILE = os.path.join(STORAGE_DIR, "sync_history.json")
ENTITY_MAPPING_FILE = os.path.join(STORAGE_DIR, "entity_mapping.json")
INCOMPLETE_PRODUCTS_FILE = os.path.join(STORAGE_DIR, "incomplete_products.json")

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "sync.log")
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# Set up logging
def setup_logging():
    """Configure logging to both file and console with rotation."""
    # Standard log format for file logging
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_formatter = logging.Formatter(log_format)
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Clear any existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Add file handler with rotation
    file_handler = RotatingFileHandler(
        os.path.join("logs", LOG_FILE),
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Custom formatter with emojis for console output
    class EmojiFormatter(logging.Formatter):
        FORMATS = {
            logging.DEBUG: '🔍 %(asctime)s | %(name)s | %(message)s',
            logging.INFO: '✅ %(asctime)s | %(name)s | %(message)s',
            logging.WARNING: '⚠️ %(asctime)s | %(name)s | %(message)s',
            logging.ERROR: '❌ %(asctime)s | %(name)s | %(message)s',
            logging.CRITICAL: '🔥 %(asctime)s | %(name)s | %(message)s'
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt, datefmt='%H:%M:%S')
            return formatter.format(record)
    
    # Add console handler with emoji formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(EmojiFormatter())
    
    # Reduzir a verbosidade no console definindo um nível mais alto para saída no console
    # INFO para mensagens principais, DEBUG será exibido apenas nos arquivos de log
    console_handler.setLevel(logging.INFO)
    
    logger.addHandler(console_handler)
    
    return logger

# Ensure the storage directory exists
os.makedirs(STORAGE_DIR, exist_ok=True)
