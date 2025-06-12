"""
Parser service for fetching and parsing news sources
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup, FeatureNotFound

from config import SOURCES, MAX_IMAGES_PER_POST
from bot.models.post import Post
from bot.utils.helpers import is_valid_image_url, make_post_id, clean_html, build_absolute_url
from bot.utils.tags import extract_tags
from bot.utils.time_utils import parse_date_from_rss

logger = logging.getLogger(__name__)


class Parser:
    """News parser service"""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.timeout = httpx.Timeout(20.0, connect=10.0)
    
    async def fetch_all_releases(self, progress_callback=None) -> List[Post]:
        """Fetch releases from all sources"""
        releases = []
        seen_titles = set()
        total_sources = len(SOURCES)
        
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for idx, source in enumerate(SOURCES):
                try:
                    # Progress callback
                    if progress_callback:
                        await progress_callback(idx + 1, total_sources, source['name'])
                    
                    logger.info(f"Fetching from {source['name']}...")
                    
                    # Fetch source
                    source_releases = await self._fetch_source(client, source, seen_titles)
                    releases.extend(source_releases)
                    
                    logger.info(f"Got {len(source_releases)} releases from {source['name']}")
                    
                except Exception as e:
                    logger.error(f"Error fetching {source['name']}: {e}")
                    continue
                
                # Small delay between sources
                await asyncio.sleep(0.5)
        
        # Sort by date (newest first)
        releases.sort(key=lambda x: x.timestamp, reverse=True)
        
        logger.info(f"Total new releases found: {len(releases)}")
        return releases
    
    async def _fetch_source(self, client: httpx.AsyncClient, source: Dict[str, Any], 
                           seen_titles: Set[str]) -> List[Post]:
        """Fetch releases from a single source"""
        try:
            response = await client.get(source["api"], headers=self.headers)
            response.raise_for_status()
            
            if source["type"] == "json":
                return await self._parse_json_source(source, response, seen_titles)
            elif source["type"] == "rss":
                return await self._parse_rss_source(source, response, seen_titles)
            else:
                logger.warning(f"Unknown source type: {source['type']}")
                return []
                
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching {source['name']}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Request error for {source['name']}: {e}")
            return []
    
    async def _parse_json_source(self, source: Dict[str, Any], response: httpx.Response,
                                seen_titles: Set[str]) -> List[Post]:
        """Parse JSON API source"""
        releases = []
        
        try:
            data = response.json()
            if not isinstance(data, list):
                logger.warning(f"Unexpected JSON format from {source['name']}")
                return releases
                
            for item in data[:10]:  # Limit to 10 posts
                post = self._parse_json_post(item, source, seen_titles)
                if post:
                    releases.append(post)
                    
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {source['name']}")
            
        return releases
    
    def _parse_json_post(self, item: Dict[str, Any], source: Dict[str, Any],
                        seen_titles: Set[str]) -> Optional[Post]:
        """Parse single JSON post"""
        try:
            # Extract basic fields
            link = item.get("link")
            if not link:
                return None
            
            # Extract title
            title_data = item.get("title", {})
            if isinstance(title_data, dict):
                title = clean_html(title_data.get("rendered", ""))
            else:
                title = str(title_data)
            
            if not title or len(title) < 10:
                return None
            
            # Check duplicates
            title_key = title.lower().strip()
            if title_key in seen_titles:
                logger.debug(f"Duplicate title: {title}")
                return None
            seen_titles.add(title_key)
            
            # Generate ID
            post_id = make_post_id(source["key"], link)
            
            # Extract date
            date_str = item.get("date") or item.get("modified")
            if date_str:
                timestamp = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now(timezone.utc)
            
            # Extract images
            images = []
            media = item.get("_embedded", {}).get("wp:featuredmedia", [])
            if media and isinstance(media, list) and len(media) > 0:
                featured_url = media[0].get("source_url")
                if featured_url and is_valid_image_url(featured_url):
                    images.append(featured_url)
            
            # Extract content
            content_data = item.get("content", {})
            if isinstance(content_data, dict):
                context = clean_html(content_data.get("rendered", ""))[:500]
            else:
                context = ""
            
            # Create post
            post = Post(
                id=post_id,
                title=title[:200],
                link=link,
                source=source["name"],
                category=source.get("category", "sneakers"),
                timestamp=timestamp.isoformat(),
                context=context,
                images=images,
                original_images=images.copy(),
                tags=extract_tags(title, context)
            )
            
            return post
            
        except Exception as e:
            logger.error(f"Error parsing JSON post: {e}")
            return None
    
    async def _parse_rss_source(self, source: Dict[str, Any], response: httpx.Response,
                               seen_titles: Set[str]) -> List[Post]:
        """Parse RSS feed source"""
        releases = []
        
        try:
            # Try different parsers
            try:
                soup = BeautifulSoup(response.text, "xml")
                items = soup.find_all("item")
            except FeatureNotFound:
                soup = BeautifulSoup(response.text, "html.parser")
                items = soup.find_all("item")
            
            if not items:
                items = soup.find_all("entry")  # Atom feeds
            
            for item in items[:10]:  # Limit to 10 posts
                post = self._parse_rss_item(item, source, seen_titles)
                if post:
                    releases.append(post)
                    
        except Exception as e:
            logger.error(f"Error parsing RSS from {source['name']}: {e}")
            
        return releases
    
    def _parse_rss_item(self, item, source: Dict[str, Any],
                       seen_titles: Set[str]) -> Optional[Post]:
        """Parse single RSS item"""
        try:
            # Extract link
            link = None
            link_elem = item.find("link")
            if link_elem:
                link = link_elem.get_text(strip=True) if link_elem.string else link_elem.get("href")
            
            if not link:
                guid = item.find("guid")
                if guid and guid.get_text(strip=True).startswith("http"):
                    link = guid.get_text(strip=True)
            
            if not link:
                return None
            
            # Extract title
            title_elem = item.find("title")
            if not title_elem:
                return None
            
            title = clean_html(title_elem.get_text(strip=True))
            if not title or len(title) < 10:
                return None
            
            # Check duplicates
            title_key = title.lower().strip()
            if title_key in seen_titles:
                logger.debug(f"Duplicate title: {title}")
                return None
            seen_titles.add(title_key)
            
            # Category filter for sneakers
            if source.get("category") == "sneakers":
                if not self._is_sneaker_related(title):
                    logger.debug(f"Non-sneaker post filtered: {title}")
                    return None
            
            # Generate ID
            post_id = make_post_id(source["key"], link)
            
            # Extract date
            pub_date = parse_date_from_rss(item)
            
            # Extract description and images
            images = []
            description = ""
            
            desc_elem = item.find("description")
            if desc_elem:
                desc_text = desc_elem.get_text()
                desc_soup = BeautifulSoup(desc_text, "html.parser")
                description = desc_soup.get_text(strip=True)[:500]
                
                # Extract first image
                first_img = desc_soup.find("img", src=True)
                if first_img:
                    img_url = first_img.get("src")
                    if img_url:
                        absolute_url = build_absolute_url(link, img_url)
                        if is_valid_image_url(absolute_url):
                            images.append(absolute_url)
            
            # Create post
            post = Post(
                id=post_id,
                title=title[:200],
                link=link,
                source=source["name"],
                category=source.get("category", "sneakers"),
                timestamp=pub_date.isoformat(),
                context=description,
                images=images,
                original_images=images.copy(),
                tags=extract_tags(title, description)
            )
            
            return post
            
        except Exception as e:
            logger.error(f"Error parsing RSS item: {e}")
            return None
    
    def _is_sneaker_related(self, text: str) -> bool:
        """Check if text is sneaker-related"""
        keywords = [
            'nike', 'adidas', 'jordan', 'yeezy', 'new balance', 'puma',
            'reebok', 'vans', 'converse', 'asics', 'sneaker', 'shoe',
            'footwear', 'release', 'drop', 'collab', 'air max', 'dunk',
            'trainer', 'runner', 'retro', 'kicks', 'sneakerhead'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)
    
    async def parse_full_content(self, post: Post) -> Post:
        """Parse full content from post URL"""
        if not post.needs_parsing:
            return post
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                # Extract all images from page
                images = await self._extract_page_images(client, post.link)
                
                if images:
                    post.images = images[:MAX_IMAGES_PER_POST]
                    post.original_images = images[:MAX_IMAGES_PER_POST]
                    logger.info(f"Found {len(images)} images for post {post.title[:30]}...")
                
                post.needs_parsing = False
                post.update_timestamp()
                
        except Exception as e:
            logger.error(f"Error parsing full content: {e}")
        
        return post
    
    async def _extract_page_images(self, client: httpx.AsyncClient, url: str) -> List[str]:
        """Extract all images from webpage"""
        images = []
        
        try:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            
            # Various image selectors
            selectors = [
                "div.gallery img",
                "div.post-gallery img",
                "div.article-gallery img",
                "div.gallery-container img",
                "figure img",
                "div.post-content img",
                "article img",
                "div[class*='gallery'] img",
                "div[class*='slider'] img",
                "div.entry-content img",
                "main img",
                ".single-content img"
            ]
            
            seen_urls = set()
            
            for selector in selectors:
                for img in soup.select(selector):
                    img_url = (img.get("src") or 
                             img.get("data-src") or 
                             img.get("data-lazy-src") or
                             img.get("data-original"))
                    
                    if not img_url:
                        continue
                    
                    # Build absolute URL
                    absolute_url = build_absolute_url(base_url, img_url)
                    
                    # Filter and dedupe
                    if (is_valid_image_url(absolute_url) and 
                        absolute_url not in seen_urls and
                        not any(skip in absolute_url.lower() for skip in ['logo', 'icon', 'avatar', 'banner'])):
                        
                        images.append(absolute_url)
                        seen_urls.add(absolute_url)
                    
                    if len(images) >= MAX_IMAGES_PER_POST:
                        break
                
                if len(images) >= MAX_IMAGES_PER_POST:
                    break
            
            logger.info(f"Extracted {len(images)} images from {url}")
            
        except Exception as e:
            logger.error(f"Error extracting images from {url}: {e}")
        
        return images
    
    async def test_sources(self) -> Dict[str, Dict[str, Any]]:
        """Test all sources and return status"""
        results = {}
        
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for source in SOURCES:
                try:
                    response = await client.get(source["api"], headers=self.headers)
                    response.raise_for_status()
                    
                    if source["type"] == "rss":
                        soup = BeautifulSoup(response.text, "xml")
                        items = soup.find_all("item") or soup.find_all("entry")
                        
                        results[source["name"]] = {
                            "status": "success",
                            "type": source["type"],
                            "category": source.get("category", "unknown"),
                            "items_count": len(items),
                            "first_title": items[0].find("title").get_text(strip=True)[:50] if items else None
                        }
                    else:
                        data = response.json()
                        count = len(data) if isinstance(data, list) else 0
                        
                        results[source["name"]] = {
                            "status": "success",
                            "type": source["type"],
                            "category": source.get("category", "unknown"),
                            "items_count": count
                        }
                        
                except Exception as e:
                    results[source["name"]] = {
                        "status": "error",
                        "error": str(e)
                    }
                
                await asyncio.sleep(0.2)  # Be nice to servers
        
        return results


# Singleton instance
parser_service = Parser()
