"""
Tag extraction and hashtag generation system
"""
import re
from typing import Dict, List, Set, Tuple
from functools import lru_cache
import logging

from config import BRAND_KEYWORDS, MODEL_KEYWORDS, RELEASE_TYPES, HASHTAGS

logger = logging.getLogger(__name__)


def extract_tags(title: str, context: str = "") -> Dict[str, List[str]]:
    """Extract tags from title and context"""
    tags = {
        "brands": [],
        "models": [],
        "types": [],
        "colors": []
    }
    
    # Combine and normalize text
    text = f"{title} {context}".lower()
    
    # Remove special characters for better matching
    text_normalized = re.sub(r'[^\w\s-]', ' ', text)
    
    # Extract brands
    for brand, keywords in BRAND_KEYWORDS.items():
        for keyword in keywords:
            # Use word boundaries for accurate matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_normalized):
                if brand not in tags["brands"]:
                    tags["brands"].append(brand)
                break
    
    # Extract models
    for model, keywords in MODEL_KEYWORDS.items():
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_normalized):
                if model not in tags["models"]:
                    tags["models"].append(model)
                break
    
    # Extract release types
    for release_type, keywords in RELEASE_TYPES.items():
        for keyword in keywords:
            if keyword in text:
                if release_type not in tags["types"]:
                    tags["types"].append(release_type)
                break
    
    # Extract colors
    colors = extract_colors(text)
    tags["colors"] = list(colors)
    
    return tags


def extract_colors(text: str) -> Set[str]:
    """Extract color mentions from text"""
    color_map = {
        # English
        "black": "black",
        "white": "white", 
        "red": "red",
        "blue": "blue",
        "green": "green",
        "yellow": "yellow",
        "purple": "purple",
        "pink": "pink",
        "orange": "orange",
        "grey": "grey",
        "gray": "grey",
        "brown": "brown",
        "gold": "gold",
        "silver": "silver",
        "navy": "navy",
        "teal": "teal",
        "cream": "cream",
        "beige": "beige",
        # Russian
        "черный": "black",
        "черн": "black",
        "белый": "white",
        "бел": "white",
        "красный": "red",
        "красн": "red",
        "синий": "blue",
        "син": "blue",
        "зеленый": "green",
        "зелен": "green",
        "желтый": "yellow",
        "желт": "yellow",
        "фиолетовый": "purple",
        "розовый": "pink",
        "роз": "pink",
        "оранжевый": "orange",
        "серый": "grey",
        "сер": "grey",
        "коричневый": "brown",
        "золотой": "gold",
        "серебряный": "silver"
    }
    
    found_colors = set()
    
    for color_term, color_eng in color_map.items():
        if re.search(r'\b' + re.escape(color_term) + r'\b', text, re.IGNORECASE):
            found_colors.add(color_eng)
    
    # Check for color codes (e.g., "Triple Black", "Core White")
    if "triple black" in text:
        found_colors.add("black")
    if "triple white" in text or "core white" in text:
        found_colors.add("white")
    
    return found_colors


def format_tags_for_display(tags: Dict[str, List[str]]) -> str:
    """Format tags for message display"""
    lines = []
    
    if tags.get("brands"):
        brands = ", ".join(brand.title() for brand in tags["brands"])
        lines.append(f"🏷 Бренд: {brands}")
    
    if tags.get("models"):
        models = ", ".join(model.upper() for model in tags["models"])
        lines.append(f"👟 Модель: {models}")
    
    if tags.get("types"):
        types_map = {
            "retro": "Ретро",
            "collab": "Коллаборация",
            "limited": "Лимитированная",
            "womens": "Женская",
            "kids": "Детская",
            "lifestyle": "Lifestyle",
            "performance": "Спортивная"
        }
        types_str = ", ".join(types_map.get(t, t.title()) for t in tags["types"])
        lines.append(f"📌 Тип: {types_str}")
    
    if tags.get("colors"):
        colors_map = {
            "black": "Черный",
            "white": "Белый",
            "red": "Красный",
            "blue": "Синий",
            "green": "Зеленый",
            "yellow": "Желтый",
            "purple": "Фиолетовый",
            "pink": "Розовый",
            "orange": "Оранжевый",
            "grey": "Серый",
            "brown": "Коричневый",
            "gold": "Золотой",
            "silver": "Серебряный",
            "navy": "Темно-синий",
            "cream": "Кремовый",
            "beige": "Бежевый"
        }
        colors_str = ", ".join(colors_map.get(c, c.title()) for c in tags["colors"])
        lines.append(f"🎨 Цвет: {colors_str}")
    
    return "\n".join(lines)


@lru_cache(maxsize=100)
def get_hashtags(title: str, category: str) -> str:
    """Generate hashtags based on title and category"""
    title_lower = title.lower()
    
    # Check specific brands/keywords
    if category == "sneakers":
        for brand, hashtags in HASHTAGS["sneakers"].items():
            if brand == "default":
                continue
                
            # Special cases
            if brand == "jordan" and ("air jordan" in title_lower or "jordan" in title_lower):
                return hashtags
            elif brand == "yeezy" and "yeezy" in title_lower:
                return hashtags
            elif brand in title_lower:
                return hashtags
        
        return HASHTAGS["sneakers"]["default"]
    
    elif category == "fashion":
        for brand, hashtags in HASHTAGS["fashion"].items():
            if brand == "default":
                continue
                
            # Special cases
            if brand == "offwhite" and ("off-white" in title_lower or "off white" in title_lower):
                return hashtags
            elif brand in title_lower:
                return hashtags
        
        return HASHTAGS["fashion"]["default"]
    
    # Default fallback
    return HASHTAGS.get(category, {}).get("default", "#streetwear #style")


def filter_posts_by_tags(posts: Dict, tag_type: str, tag_value: str) -> List[str]:
    """Filter posts by specific tag"""
    filtered = []
    
    for post_id, post in posts.items():
        tags = post.get("tags", {})
        
        if tag_type == "brand" and tag_value in tags.get("brands", []):
            filtered.append(post_id)
        elif tag_type == "model" and tag_value in tags.get("models", []):
            filtered.append(post_id)
        elif tag_type == "type" and tag_value in tags.get("types", []):
            filtered.append(post_id)
        elif tag_type == "color" and tag_value in tags.get("colors", []):
            filtered.append(post_id)
    
    return filtered


def get_all_unique_tags(posts: Dict) -> Dict[str, Set[str]]:
    """Get all unique tags from posts collection"""
    all_tags = {
        "brands": set(),
        "models": set(),
        "types": set(),
        "colors": set()
    }
    
    for post in posts.values():
        tags = post.get("tags", {})
        
        all_tags["brands"].update(tags.get("brands", []))
        all_tags["models"].update(tags.get("models", []))
        all_tags["types"].update(tags.get("types", []))
        all_tags["colors"].update(tags.get("colors", []))
    
    return all_tags


def suggest_tags(text: str) -> List[Tuple[str, float]]:
    """Suggest tags with confidence scores"""
    suggestions = []
    text_lower = text.lower()
    
    # Check brands
    for brand, keywords in BRAND_KEYWORDS.items():
        score = 0.0
        matched_keywords = 0
        
        for keyword in keywords:
            if keyword in text_lower:
                matched_keywords += 1
                # Higher score for exact brand name
                if keyword == brand:
                    score += 1.0
                else:
                    score += 0.5
        
        if score > 0:
            confidence = min(score / len(keywords), 1.0)
            suggestions.append((f"brand:{brand}", confidence))
    
    # Sort by confidence
    suggestions.sort(key=lambda x: x[1], reverse=True)
    
    return suggestions[:10]  # Return top 10 suggestions


def enrich_tags(existing_tags: Dict[str, List[str]], text: str) -> Dict[str, List[str]]:
    """Enrich existing tags with additional context"""
    enriched = existing_tags.copy()
    
    # Add related brands
    if "yeezy" in existing_tags.get("models", []) and "adidas" not in enriched.get("brands", []):
        enriched.setdefault("brands", []).append("adidas")
    
    # Add related types
    if any(brand in ["supreme", "palace", "stussy"] for brand in enriched.get("brands", [])):
        if "collab" not in enriched.get("types", []):
            enriched.setdefault("types", []).append("lifestyle")
    
    return enriched
