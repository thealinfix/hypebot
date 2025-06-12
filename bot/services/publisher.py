"""
Post publishing service
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from telegram import Bot, InputMediaPhoto
from telegram.error import TelegramError
from telegram.constants import ParseMode

from bot.models.post import Post
from bot.utils.state import get_state, update_state, save_state

logger = logging.getLogger(__name__)


class Publisher:
    """Service for publishing posts to Telegram"""
    
    def __init__(self):
        self.max_caption_length = 1024
        self.max_media_group_size = 10
    
    async def publish_post(self, bot: Bot, post: Post, 
                          channel: Optional[str] = None) -> bool:
        """Publish post to channel"""
        try:
            state = await get_state()
            if not channel:
                channel = state.get("channel")
            
            if not channel:
                logger.error("No channel specified for publishing")
                return False
            
            logger.info(f"Publishing post {post.id} to {channel}")
            
            # Build media group
            media_group = await self._build_media_group(post, for_channel=True)
            
            # Send to channel
            if media_group:
                # Send as media group
                await bot.send_media_group(channel, media_group)
            else:
                # Send as text message
                caption = self._build_caption(post, for_channel=True)
                await bot.send_message(
                    channel,
                    caption,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False
                )
            
            # Update post status
            post.mark_as_published()
            
            # Update state
            state = await get_state()
            
            # Add to sent links
            if post.link not in state["sent_links"]:
                state["sent_links"].append(post.link)
                # Keep only last 1000 links
                if len(state["sent_links"]) > 1000:
                    state["sent_links"] = state["sent_links"][-500:]
            
            # Remove from pending
            state["pending"].pop(post.id, None)
            
            # Remove from favorites
            if post.id in state.get("favorites", []):
                state["favorites"].remove(post.id)
            
            # Update last publish time for auto-publish
            if state.get("auto_publish"):
                await update_state("last_auto_publish", datetime.now(timezone.utc).isoformat())
            
            await save_state()
            
            logger.info(f"Successfully published post {post.id}")
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error publishing post {post.id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing post {post.id}: {e}")
            return False
    
    async def _build_media_group(self, post: Post, 
                               for_channel: bool = False) -> List[InputMediaPhoto]:
        """Build media group for post"""
        media = []
        
        # Get all images
        images = post.get_display_images(self.max_media_group_size)
        
        if not images:
            return media
        
        # Build caption
        caption = self._build_caption(post, for_channel)
        
        # First image with caption
        media.append(InputMediaPhoto(
            media=images[0],
            caption=caption,
            parse_mode=ParseMode.HTML
        ))
        
        # Rest of images without caption
        for image_url in images[1:]:
            media.append(InputMediaPhoto(media=image_url))
        
        return media
    
    def _build_caption(self, post: Post, for_channel: bool = False) -> str:
        """Build caption for post"""
        caption = post.description or post.context or post.title
        
        if for_channel:
            # Add hashtags
            hashtags = post.get_hashtags()
            
            # Add source
            source_emojis = {
                "SneakerNews": "📰",
                "Hypebeast": "🔥",
                "Highsnobiety": "💎",
                "Hypebeast Footwear": "👟",
                "Hypebeast Fashion": "👔",
                "Highsnobiety Sneakers": "✨",
                "Highsnobiety Fashion": "🎨"
            }
            source_emoji = source_emojis.get(post.source, "📍")
            source_text = f"\n\n{source_emoji} {post.source}"
            
            # Add link
            category_emoji = "👟" if post.category == "sneakers" else "👔"
            link_text = f"\n{category_emoji} <a href=\"{post.link}\">Читать полностью</a>"
            
            # Check total length
            total_length = len(caption) + len(source_text) + len(link_text) + len(hashtags) + 10
            
            if total_length < self.max_caption_length:
                caption += source_text + link_text + "\n\n" + hashtags
            elif len(caption) + len(hashtags) + 10 < self.max_caption_length:
                caption += "\n\n" + hashtags
            else:
                # Truncate caption to fit hashtags
                max_caption = self.max_caption_length - len(hashtags) - 10
                caption = caption[:max_caption] + "..." + "\n\n" + hashtags
        
        return caption
    
    async def send_for_moderation(self, bot: Bot, post: Post, 
                                admin_chat_id: int) -> bool:
        """Send post for moderation"""
        try:
            from bot.utils.keyboards import KeyboardBuilder
            
            # Build moderation keyboard
            keyboard = KeyboardBuilder.moderation(post.id)
            
            # Build preview text
            preview_text = self._build_moderation_text(post)
            
            # Send media if available
            media_group = await self._build_media_group(post, for_channel=False)
            
            if media_group:
                # Send media group first
                await bot.send_media_group(admin_chat_id, media_group)
                
                # Then send control message
                await bot.send_message(
                    admin_chat_id,
                    preview_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
            else:
                # Send text message only
                await bot.send_message(
                    admin_chat_id,
                    preview_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                )
            
            logger.info(f"Sent post {post.id} for moderation")
            return True
            
        except Exception as e:
            logger.error(f"Error sending post for moderation: {e}")
            return False
    
    def _build_moderation_text(self, post: Post) -> str:
        """Build moderation preview text"""
        from bot.utils.time_utils import format_date_for_display
        
        category_emoji = "👟" if post.category == "sneakers" else "👔"
        date_str = format_date_for_display(post.timestamp)
        hashtags = post.get_hashtags()
        
        # Image info
        img_info = ""
        generated_count = len(post.generated_images)
        original_count = len(post.original_images)
        
        if generated_count > 0:
            img_info = f"\n🎨 Сгенерировано: {generated_count}, оригинальных: {original_count}"
        else:
            img_info = f"\n🖼 Изображений: {original_count}"
        
        # Tags info
        tags_display = post.get_formatted_tags()
        
        text = (
            f"📅 {date_str}\n"
            f"{category_emoji} <b>{post.title}</b>\n\n"
        )
        
        if tags_display:
            text += f"{tags_display}\n\n"
        
        text += (
            f"{post.description[:400]}\n"
            f"\n📍 Источник: {post.source}"
            f"\n🔗 Статья: {post.link}"
            f"{img_info}\n\n"
            f"{hashtags}\n\n"
            f"🆔 ID: {post.id}"
        )
        
        return text
    
    async def publish_scheduled(self, bot: Bot) -> int:
        """Publish all due scheduled posts"""
        published_count = 0
        state = await get_state()
        scheduled_posts = state.get("scheduled_posts", {})
        
        now = datetime.now(timezone.utc)
        to_publish = []
        
        # Find due posts
        for post_id, schedule_info in scheduled_posts.items():
            try:
                scheduled_time = datetime.fromisoformat(
                    schedule_info["time"].replace('Z', '+00:00')
                )
                
                if now >= scheduled_time:
                    to_publish.append((post_id, schedule_info))
                    
            except Exception as e:
                logger.error(f"Error checking scheduled post {post_id}: {e}")
        
        # Publish due posts
        for post_id, schedule_info in to_publish:
            try:
                # Get post data
                if "record" in schedule_info:
                    post_data = schedule_info["record"]
                    post = Post.from_dict(post_data)
                else:
                    # Try to find in pending
                    post_data = state["pending"].get(post_id)
                    if not post_data:
                        logger.warning(f"Scheduled post {post_id} not found")
                        continue
                    post = Post.from_dict(post_data)
                
                # Publish
                success = await self.publish_post(bot, post)
                
                if success:
                    published_count += 1
                    
                    # Remove from scheduled
                    state["scheduled_posts"].pop(post_id, None)
                    
                    # Notify admin
                    admin_chat_id = state.get("admin_chat_id")
                    if admin_chat_id:
                        await bot.send_message(
                            admin_chat_id,
                            f"✅ Запланированный пост опубликован:\n{post.title[:50]}...",
                            parse_mode=ParseMode.HTML
                        )
                        
            except Exception as e:
                logger.error(f"Error publishing scheduled post {post_id}: {e}")
        
        if published_count > 0:
            await save_state()
        
        return published_count
    
    async def publish_from_favorites(self, bot: Bot) -> bool:
        """Publish next post from favorites (for auto-publish)"""
        state = await get_state()
        
        if not state.get("auto_publish"):
            return False
        
        # Check interval
        last_publish = state.get("last_auto_publish")
        if last_publish:
            last_time = datetime.fromisoformat(last_publish.replace('Z', '+00:00'))
            interval = state.get("publish_interval", 3600)
            
            if (datetime.now(timezone.utc) - last_time).seconds < interval:
                return False
        
        # Get next favorite
        favorites = state.get("favorites", [])
        if not favorites:
            return False
        
        # Find first favorite that's still pending
        for fav_id in favorites:
            if fav_id in state["pending"]:
                post_data = state["pending"][fav_id]
                post = Post.from_dict(post_data)
                
                # Publish
                success = await self.publish_post(bot, post)
                
                if success:
                    # Notify admin
                    admin_chat_id = state.get("admin_chat_id")
                    if admin_chat_id:
                        await bot.send_message(
                            admin_chat_id,
                            f"🤖 Автоматически опубликован пост из избранного:\n{post.title[:50]}...",
                            parse_mode=ParseMode.HTML
                        )
                    
                    return True
        
        return False
    
    async def publish_thought(self, bot: Bot, thought_data: Dict[str, Any]) -> bool:
        """Publish thought/personal post"""
        try:
            state = await get_state()
            channel = state.get("channel")
            
            if not channel:
                logger.error("No channel specified for publishing")
                return False
            
            text = thought_data.get("text", "")
            image_url = thought_data.get("image_url")
            
            if image_url:
                # Send as photo
                await bot.send_photo(
                    channel,
                    image_url,
                    caption=text,
                    parse_mode=ParseMode.HTML
                )
            else:
                # Send as text
                await bot.send_message(
                    channel,
                    text,
                    parse_mode=ParseMode.HTML
                )
            
            logger.info("Successfully published thought")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing thought: {e}")
            return False


# Singleton instance
publisher = Publisher()
