# api/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# base directory
BASE_DIR = Path(__file__).parent.parent

# Content Directories
CONTENT_DIR = BASE_DIR / "content"
POSTS_DIR = CONTENT_DIR / "posts"
PAGES_DIR = CONTENT_DIR / "pages"
ZINES_DIR = CONTENT_DIR / "zines"
PHOTOS_DIR = CONTENT_DIR / "photos"

# Photo sizes
THUMBNAIL_SIZE = (300, 300)  # Instagram-style square thumbnails
MEDIUM_SIZE = (1080, 1080)  # Max dimension while maintaining aspect ratio
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB max upload size

# Supported image formats
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# Photos per page for pagination
PHOTOS_PER_PAGE = 12

# Site configuration
SITE_TITLE = "voidfemme"
SITE_DESCRIPTION = "A space for thoughts, code, and zines."
SITE_AUTHOR = "Rose Proctor"
SITE_URL = "https://voidfemme.com"

# ActivityPub configuration
ACTIVITYPUB_USERNAME = "rose"
ACTIVITYPUB_DOMAIN = "voidfemme.com"
ACTIVITYPUB_ACTOR_URL = f"https://{ACTIVITYPUB_DOMAIN}/users/{ACTIVITYPUB_USERNAME}"

# Database
DB_PATH = BASE_DIR / "api" / "webmentions.db"

# Development settings
DEBUG = os.getenv("FLASK_ENV") == "development"

# Create required Directories
PHOTOS_DIR.mkdir(exist_ok=True)
(PHOTOS_DIR / "original").mkdir(exist_ok=True)
(PHOTOS_DIR / "thumbnail").mkdir(exist_ok=True)
(PHOTOS_DIR / "medium").mkdir(exist_ok=True)

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your-bot-token-here")
ALLOWED_TELEGRAM_USERS = os.getenv("ALLOWED_TELEGRAM_USERS", "").split(",")

# Email configuration
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_DEFAULT_SENDER = ("voidfemme", os.getenv("MAIL_USERNAME"))
