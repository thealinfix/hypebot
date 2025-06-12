"""
Configuration module for HypeBot
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Telegram settings
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL", "@channelusername")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Redis settings (optional)
REDIS_URL = os.getenv("REDIS_URL")

# Bot settings
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "1800"))
MAX_PENDING_POSTS = int(os.getenv("MAX_PENDING_POSTS", "100"))
MAX_POST_AGE_DAYS = int(os.getenv("MAX_POST_AGE_DAYS", "7"))
MAX_IMAGES_PER_POST = int(os.getenv("MAX_IMAGES_PER_POST", "10"))
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow")

# Files
STATE_FILE = DATA_DIR / "state.json"
LOG_FILE = DATA_DIR / "bot.log"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Convert ADMIN_CHAT_ID to int
if ADMIN_CHAT_ID:
    try:
        ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
    except ValueError:
        print(f"Warning: ADMIN_CHAT_ID must be a number, got: {ADMIN_CHAT_ID}")
        ADMIN_CHAT_ID = None

# Validation
def validate_config():
    """Validate required configuration"""
    errors = []
    
    if not TELEGRAM_TOKEN:
        errors.append("TELEGRAM_TOKEN not set")
    
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY not set")
    
    if errors:
        raise ValueError("Configuration errors: " + ", ".join(errors))

# Image generation styles
IMAGE_STYLES = {
    "sneakers": {
        "prompt_template": "Modern minimalist sneaker promotional image, {title}, clean background, professional product photography, studio lighting, high quality, 4k",
        "style": "photographic"
    },
    "fashion": {
        "prompt_template": "Fashion editorial style image, {title}, trendy streetwear aesthetic, urban background, magazine quality",
        "style": "editorial"
    },
    "thoughts": {
        "prompt_template": "Artistic abstract representation of {topic}, modern digital art, vibrant colors, emotional expression, Instagram story format",
        "style": "artistic"
    },
    "custom": {
        "prompt_template": "{custom_prompt}",
        "style": "creative"
    }
}

# Hashtags
HASHTAGS = {
    "sneakers": {
        "nike": "#nike #sneakers #кроссовки #найк #никебутик",
        "adidas": "#adidas #sneakers #кроссовки #адидас #threestripes",
        "jordan": "#jordan #airjordan #кроссовки #джордан #jumpman",
        "newbalance": "#newbalance #nb #кроссовки #ньюбаланс #madeinusa",
        "puma": "#puma #sneakers #кроссовки #пума #pumafamily",
        "yeezy": "#yeezy #adidas #кроссовки #изи #kanye",
        "asics": "#asics #sneakers #кроссовки #асикс #geltechnology",
        "reebok": "#reebok #sneakers #кроссовки #рибок #classic",
        "vans": "#vans #sneakers #кроссовки #ванс #offthewall",
        "converse": "#converse #sneakers #кроссовки #конверс #allstar",
        "default": "#sneakers #кроссовки #streetwear #обувь #sneakerhead"
    },
    "fashion": {
        "supreme": "#supreme #streetwear #fashion #суприм #hypebeast",
        "offwhite": "#offwhite #fashion #streetwear #virgilabloh",
        "stussy": "#stussy #streetwear #fashion #stussytribe",
        "palace": "#palace #streetwear #fashion #palaceskateboards",
        "default": "#fashion #мода #streetwear #style #стиль #outfit"
    }
}

# News sources
SOURCES = [
    {
        "key": "sneakernews",
        "name": "SneakerNews",
        "type": "json",
        "api": "https://sneakernews.com/wp-json/wp/v2/posts?per_page=10&_embed",
        "category": "sneakers"
    },
    {
        "key": "hypebeast",
        "name": "Hypebeast Footwear",
        "type": "rss",
        "api": "https://hypebeast.com/footwear/feed",
        "category": "sneakers"
    },
    {
        "key": "highsnobiety",
        "name": "Highsnobiety Sneakers",
        "type": "rss",
        "api": "https://www.highsnobiety.com/tag/sneakers/feed/",
        "category": "sneakers"
    },
    {
        "key": "hypebeast_fashion",
        "name": "Hypebeast Fashion",
        "type": "rss",
        "api": "https://hypebeast.com/fashion/feed",
        "category": "fashion"
    },
    {
        "key": "highsnobiety_fashion",
        "name": "Highsnobiety Fashion",
        "type": "rss",
        "api": "https://www.highsnobiety.com/tag/fashion/feed/",
        "category": "fashion"
    }
]

# Brand keywords for tagging
BRAND_KEYWORDS = {
    "nike": ["nike", "air max", "air force", "dunk", "blazer", "cortez", "vapormax", "pegasus"],
    "adidas": ["adidas", "yeezy", "boost", "ultraboost", "nmd", "gazelle", "samba", "campus"],
    "jordan": ["jordan", "air jordan", "aj1", "aj4", "aj11", "jumpman"],
    "newbalance": ["new balance", "nb", "990", "991", "992", "993", "2002r", "550"],
    "asics": ["asics", "gel", "gel-lyte", "gel-kayano", "gel-1090"],
    "puma": ["puma", "suede", "clyde", "rs-x"],
    "reebok": ["reebok", "classic", "club c", "question"],
    "vans": ["vans", "old skool", "sk8-hi", "authentic", "era"],
    "converse": ["converse", "chuck taylor", "all star", "one star"],
    "salomon": ["salomon", "xt-6", "speedcross"],
}

# Model keywords
MODEL_KEYWORDS = {
    "airmax": ["air max", "airmax", "am1", "am90", "am95", "am97"],
    "airforce": ["air force", "af1", "air force 1"],
    "dunk": ["dunk", "dunk low", "dunk high", "sb dunk"],
    "yeezy": ["yeezy", "boost 350", "boost 700", "foam runner"],
    "jordan1": ["jordan 1", "aj1", "air jordan 1"],
    "jordan4": ["jordan 4", "aj4", "air jordan 4"],
    "ultraboost": ["ultraboost", "ultra boost"],
    "990": ["990", "990v", "990v5", "990v6"]
}

# Release types
RELEASE_TYPES = {
    "retro": ["retro", "og", "original", "vintage"],
    "collab": ["collab", "collaboration", "x ", " x ", "partner"],
    "limited": ["limited", "exclusive", "rare", "special edition"],
    "womens": ["women", "wmns", "female"],
    "kids": ["kids", "gs", "gradeschool", "youth"],
    "lifestyle": ["lifestyle", "casual", "street"],
    "performance": ["performance", "running", "basketball", "training"]
}
