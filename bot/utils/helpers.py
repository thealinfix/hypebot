"""
Helper utilities
"""
import hashlib
import re
from urllib.parse import urlparse, urljoin
from typing import Optional, List, Dict, Any
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


def make_post_id(source: str, link: str) -> str:
    """Create unique ID for post"""
    return hashlib.md5(f"{source}|{link}".encode()).hexdigest()[:12]


@lru_cache(maxsize=1000)
def is_valid_image_url(url: str) -> bool:
    """Check if URL is valid image URL with caching"""
    if not url or not isinstance(url, str):
        return False
    
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False
    
    # Check extension
    valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg')
    path_lower = parsed.path.lower()
    
    # Direct extension check
    if any(path_lower.endswith(ext) for ext in valid_extensions):
        return True
    
    # Check for image in query params (CDN urls)
    if 'image' in path_lower or 'img' in path_lower or 'photo' in path_lower:
        return True
    
    return False


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text with suffix"""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)].strip() + suffix


def clean_html(text: str) -> str:
    """Clean HTML tags from text"""
    if not text:
        return ""
    
    from bs4 import BeautifulSoup
    
    # Remove scripts and styles
    soup = BeautifulSoup(text, "html.parser")
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text
    cleaned = soup.get_text(separator=" ", strip=True)
    
    # Remove multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned.strip()


def format_number(num: int) -> str:
    """Format large numbers"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return str(num)


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return None


def validate_channel_format(channel: str) -> bool:
    """Validate Telegram channel format"""
    if not channel:
        return False
    
    # Public channel (@username)
    if channel.startswith("@"):
        # Check username rules
        username = channel[1:]
        if len(username) < 5 or len(username) > 32:
            return False
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False
        return True
    
    # Private channel (chat ID)
    if channel.lstrip("-").isdigit() and len(channel) > 5:
        try:
            chat_id = int(channel)
            # Telegram chat IDs for channels start with -100
            return str(chat_id).startswith("-100")
        except ValueError:
            return False
    
    return False


def escape_markdown(text: str, version: int = 2) -> str:
    """Escape markdown special characters"""
    if version == 1:
        escape_chars = r'_*`['
    else:  # MarkdownV2
        escape_chars = r'_*[]()~`>#+-=|{}.!'
    
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


def build_absolute_url(base_url: str, relative_url: str) -> str:
    """Build absolute URL from base and relative"""
    if not relative_url:
        return ""
    
    # Already absolute
    if relative_url.startswith(('http://', 'https://')):
        return relative_url
    
    return urljoin(base_url, relative_url)


def extract_images_from_html(html: str, base_url: str) -> List[str]:
    """Extract all image URLs from HTML"""
    if not html:
        return []
    
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html, "html.parser")
    images = []
    seen = set()
    
    # Find all img tags
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if src and src not in seen:
            absolute_url = build_absolute_url(base_url, src)
            if is_valid_image_url(absolute_url):
                images.append(absolute_url)
                seen.add(src)
    
    # Find background images in style attributes
    for elem in soup.find_all(style=True):
        style = elem.get("style", "")
        matches = re.findall(r'url\(["\']?([^"\'()]+)["\']?\)', style)
        for match in matches:
            if match not in seen:
                absolute_url = build_absolute_url(base_url, match)
                if is_valid_image_url(absolute_url):
                    images.append(absolute_url)
                    seen.add(match)
    
    return images


def safe_dict_get(d: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Safely get nested dictionary value using dot notation"""
    try:
        keys = path.split('.')
        value = d
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value
    except Exception:
        return default


def chunks(lst: List[Any], n: int) -> List[List[Any]]:
    """Yield successive n-sized chunks from list"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filename for filesystem"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Limit length
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        if ext:
            max_name_length = max_length - len(ext) - 1
            filename = f"{name[:max_name_length]}.{ext}"
        else:
            filename = filename[:max_length]
    
    return filename.strip()


def is_valid_url(url: str) -> bool:
    """Check if string is valid URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False
