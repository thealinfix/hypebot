"""
Task scheduling service
"""
import logging
from datetime import datetime, timezone
from typing import Callable, Any

from telegram.ext import Application, JobQueue
from telegram.ext import ContextTypes

from bot.services.parser import parser_service
from bot.services.publisher import publisher
from bot.utils.state import get_state, update_state
from bot.models.post import Post
from config import CHECK_INTERVAL, ADMIN_CHAT_ID

logger = logging.getLogger(__name__)


class Scheduler:
    """Service for scheduling periodic tasks"""
    
    def __init__(self):
        self.jobs = {}
    
    def setup(self, application: Application) -> None:
        """Setup scheduled jobs"""
        job_queue = application.job_queue
        
        # Schedule periodic check for new releases
        self.jobs['check_releases'] = job_queue.run_repeating(
            self.check_releases_job,
            interval=CHECK_INTERVAL,
            first=30,  # Start after 30 seconds
            name='check_releases'
        )
        
        # Schedule periodic check for scheduled posts
        self.jobs['check_scheduled'] = job_queue.run_repeating(
            self.check_scheduled_posts_job,
            interval=60,  # Check every minute
            first=10,
            name='check_scheduled'
        )
        
        # Schedule auto-publish check
        self.jobs['auto_publish'] = job_queue.run_repeating(
            self.auto_publish_job,
            interval=300,  # Check every 5 minutes
            first=60,
            name='auto_publish'
        )
        
        # Schedule cleanup job
        self.jobs['cleanup'] = job_queue.run_daily(
            self.cleanup_job,
            time=datetime.now(timezone.utc).replace(hour=3, minute=0, second=0),  # 3 AM UTC
            name='cleanup'
        )
        
        logger.info("Scheduled jobs setup completed")
    
    async def check_releases_job(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Job to check for new releases"""
        bot = context.bot
        
        try:
            logger.info("Starting scheduled release check...")
            
            # Send notification to admin if configured
            progress_msg = None
            if ADMIN_CHAT_ID:
                try:
                    progress_msg = await bot.send_message(
                        ADMIN_CHAT_ID,
                        "🔄 Начинаю проверку источников...",
                    )
                except Exception as e:
                    logger.error(f"Error sending progress message: {e}")
            
            # Progress callback
            async def progress_callback(current: int, total: int, source_name: str):
                if progress_msg:
                    try:
                        await bot.edit_message_text(
                            f"🔄 Проверяю источники... ({current}/{total})\n"
                            f"📍 Сейчас: {source_name}",
                            progress_msg.chat.id,
                            progress_msg.message_id
                        )
                    except Exception:
                        pass
            
            # Fetch new releases
            new_releases = await parser_service.fetch_all_releases(progress_callback)
            
            if not new_releases:
                if progress_msg:
                    await bot.edit_message_text(
                        "📭 Новых релизов не найдено",
                        progress_msg.chat.id,
                        progress_msg.message_id
                    )
                return
            
            # Load state and add new releases
            state = await get_state()
            added_count = 0
            
            for release in new_releases:
                if release.id not in state["pending"] and release.link not in state["sent_links"]:
                    state["pending"][release.id] = release.to_dict()
                    added_count += 1
            
            if added_count > 0:
                await update_state("pending", state["pending"])
                logger.info(f"Added {added_count} new posts to queue")
                
                # Notify admin
                if progress_msg:
                    # Group posts by date
                    posts_by_date = {}
                    for post_data in state["pending"].values():
                        post = Post.from_dict(post_data)
                        date_str = post.timestamp.split('T')[0]
                        if date_str not in posts_by_date:
                            posts_by_date[date_str] = []
                        posts_by_date[date_str].append(post)
                    
                    # Build summary
                    summary = f"🆕 Найдено <b>{added_count}</b> новых постов!\n\n"
                    
                    for date, posts in sorted(posts_by_date.items(), reverse=True)[:3]:
                        summary += f"📅 <b>{date}</b> ({len(posts)} постов)\n"
                        
                        # Group by source
                        by_source = {}
                        for post in posts:
                            if post.source not in by_source:
                                by_source[post.source] = 0
                            by_source[post.source] += 1
                        
                        for src, count in by_source.items():
                            summary += f"  • {src}: {count}\n"
                        summary += "\n"
                    
                    summary += f"📊 Всего в очереди: {len(state['pending'])}\n\n"
                    summary += "Используйте /preview для просмотра"
                    
                    await bot.edit_message_text(
                        summary,
                        progress_msg.chat.id,
                        progress_msg.message_id,
                        parse_mode='HTML'
                    )
            else:
                if progress_msg:
                    await bot.edit_message_text(
                        "✅ Проверка завершена, новых уникальных постов не найдено",
                        progress_msg.chat.id,
                        progress_msg.message_id
                    )
            
        except Exception as e:
            logger.error(f"Error in check_releases_job: {e}", exc_info=True)
            
            if ADMIN_CHAT_ID:
                try:
                    await bot.send_message(
                        ADMIN_CHAT_ID,
                        f"❌ Ошибка при проверке релизов: {str(e)}"
                    )
                except Exception:
                    pass
    
    async def check_scheduled_posts_job(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Job to check and publish scheduled posts"""
        bot = context.bot
        
        try:
            published_count = await publisher.publish_scheduled(bot)
            
            if published_count > 0:
                logger.info(f"Published {published_count} scheduled posts")
                
        except Exception as e:
            logger.error(f"Error in check_scheduled_posts_job: {e}")
    
    async def auto_publish_job(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Job for auto-publishing from favorites"""
        bot = context.bot
        
        try:
            state = await get_state()
            
            if not state.get("auto_publish"):
                return
            
            success = await publisher.publish_from_favorites(bot)
            
            if success:
                logger.info("Auto-published post from favorites")
                
        except Exception as e:
            logger.error(f"Error in auto_publish_job: {e}")
    
    async def cleanup_job(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Job to clean up old data"""
        bot = context.bot
        
        try:
            logger.info("Starting cleanup job...")
            
            state = await get_state()
            
            # Clean old posts
            from bot.utils.state import clean_old_posts
            removed_count = await clean_old_posts(state)
            
            if removed_count > 0:
                await update_state("pending", state["pending"])
                logger.info(f"Cleaned up {removed_count} old posts")
            
            # Clean old scheduled posts
            now = datetime.now(timezone.utc)
            scheduled = state.get("scheduled_posts", {})
            expired = []
            
            for post_id, schedule_info in scheduled.items():
                try:
                    scheduled_time = datetime.fromisoformat(
                        schedule_info["time"].replace('Z', '+00:00')
                    )
                    
                    # Remove if more than 1 day overdue
                    if (now - scheduled_time).days > 1:
                        expired.append(post_id)
                        
                except Exception:
                    expired.append(post_id)
            
            for post_id in expired:
                scheduled.pop(post_id, None)
            
            if expired:
                await update_state("scheduled_posts", scheduled)
                logger.info(f"Removed {len(expired)} expired scheduled posts")
            
            # Trim sent links
            sent_links = state.get("sent_links", [])
            if len(sent_links) > 1000:
                state["sent_links"] = sent_links[-500:]
                await update_state("sent_links", state["sent_links"])
                logger.info("Trimmed sent links list")
            
            # Notify admin
            if ADMIN_CHAT_ID and (removed_count > 0 or expired):
                await bot.send_message(
                    ADMIN_CHAT_ID,
                    f"🧹 Очистка завершена:\n"
                    f"• Удалено старых постов: {removed_count}\n"
                    f"• Удалено просроченных запланированных: {len(expired)}"
                )
                
        except Exception as e:
            logger.error(f"Error in cleanup_job: {e}")
    
    def add_once_job(self, job_queue: JobQueue, callback: Callable, 
                    when: datetime, data: Any = None, name: str = None) -> None:
        """Add a one-time job"""
        job = job_queue.run_once(
            callback,
            when=when,
            data=data,
            name=name
        )
        
        if name:
            self.jobs[name] = job
        
        logger.info(f"Scheduled one-time job: {name or 'unnamed'} at {when}")
    
    def remove_job(self, name: str) -> bool:
        """Remove a scheduled job"""
        if name in self.jobs:
            job = self.jobs[name]
            job.schedule_removal()
            del self.jobs[name]
            logger.info(f"Removed job: {name}")
            return True
        return False
    
    def get_job_info(self) -> dict:
        """Get information about scheduled jobs"""
        info = {}
        
        for name, job in self.jobs.items():
            info[name] = {
                "enabled": job.enabled,
                "removed": job.removed,
                "next_run": job.next_t.isoformat() if job.next_t else None
            }
        
        return info


# Singleton instance
scheduler = Scheduler()


def setup_jobs(application: Application) -> None:
    """Setup all scheduled jobs"""
    scheduler.setup(application)
