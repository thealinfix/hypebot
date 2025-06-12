"""
Admin-specific handlers and functionality
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import ADMIN_CHAT_ID
from bot.utils.decorators import admin_only, error_handler, log_action
from bot.utils.state import get_state, save_state, reset_state
from bot.utils.keyboards import KeyboardBuilder
from bot.models.post import Post, PostCollection

logger = logging.getLogger(__name__)


@error_handler
@admin_only
@log_action("broadcast command")
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast message to all bot users (if implemented)"""
    await update.message.reply_text(
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Функция рассылки не реализована в текущей версии бота.\n"
        "Бот работает только с администратором и каналом.",
        parse_mode=ParseMode.HTML
    )


@error_handler
@admin_only
@log_action("export command")
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Export bot data"""
    msg = await update.message.reply_text("📤 Экспортирую данные...")
    
    try:
        state = await get_state()
        
        # Create summary
        summary = {
            "export_date": datetime.now(timezone.utc).isoformat(),
            "stats": {
                "pending_posts": len(state.get("pending", {})),
                "scheduled_posts": len(state.get("scheduled_posts", {})),
                "favorites": len(state.get("favorites", [])),
                "sent_posts": len(state.get("sent_links", [])),
                "generated_images": len(state.get("generated_images", {}))
            },
            "settings": {
                "channel": state.get("channel", "Not set"),
                "timezone": state.get("timezone", "UTC"),
                "auto_publish": state.get("auto_publish", False),
                "publish_interval": state.get("publish_interval", 3600)
            }
        }
        
        # Format as text
        export_text = (
            "📊 <b>HypeBot Data Export</b>\n"
            f"📅 {summary['export_date']}\n\n"
            "<b>Statistics:</b>\n"
            f"• Pending: {summary['stats']['pending_posts']}\n"
            f"• Scheduled: {summary['stats']['scheduled_posts']}\n"
            f"• Favorites: {summary['stats']['favorites']}\n"
            f"• Published: {summary['stats']['sent_posts']}\n"
            f"• Generated images: {summary['stats']['generated_images']}\n\n"
            "<b>Settings:</b>\n"
            f"• Channel: {summary['settings']['channel']}\n"
            f"• Timezone: {summary['settings']['timezone']}\n"
            f"• Auto-publish: {'✅' if summary['settings']['auto_publish'] else '❌'}\n"
            f"• Interval: {summary['settings']['publish_interval'] // 60} min"
        )
        
        await msg.edit_text(export_text, parse_mode=ParseMode.HTML)
        
        # Send state file if requested
        if context.args and "full" in context.args:
            import json
            from io import BytesIO
            
            # Create JSON file
            json_data = json.dumps(state, ensure_ascii=False, indent=2)
            file = BytesIO(json_data.encode('utf-8'))
            file.name = f"hypebot_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            file.seek(0)
            
            await update.message.reply_document(
                document=file,
                filename=file.name,
                caption="📎 Полный экспорт состояния бота"
            )
            
    except Exception as e:
        logger.error(f"Error in export_command: {e}")
        await msg.edit_text("❌ Ошибка при экспорте данных")


@error_handler
@admin_only
@log_action("analytics command")
async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed analytics"""
    state = await get_state()
    
    # Analyze posts
    collection = PostCollection.from_dict(state.get("pending", {}))
    
    # Time-based analytics
    now = datetime.now(timezone.utc)
    today_posts = []
    week_posts = []
    month_posts = []
    
    for post in collection.get_all():
        try:
            post_date = datetime.fromisoformat(post.timestamp.replace('Z', '+00:00'))
            age = now - post_date
            
            if age.days == 0:
                today_posts.append(post)
            if age.days < 7:
                week_posts.append(post)
            if age.days < 30:
                month_posts.append(post)
        except:
            continue
    
    # Source analytics
    source_stats = {}
    for post in collection.get_all():
        source = post.source
        if source not in source_stats:
            source_stats[source] = {"count": 0, "brands": set()}
        source_stats[source]["count"] += 1
        source_stats[source]["brands"].update(post.tags.get("brands", []))
    
    # Brand analytics
    brand_stats = {}
    for post in collection.get_all():
        for brand in post.tags.get("brands", []):
            brand_stats[brand] = brand_stats.get(brand, 0) + 1
    
    # Build analytics text
    analytics_text = (
        "📊 <b>Детальная аналитика</b>\n\n"
        "<b>Посты по времени:</b>\n"
        f"• Сегодня: {len(today_posts)}\n"
        f"• За неделю: {len(week_posts)}\n"
        f"• За месяц: {len(month_posts)}\n"
        f"• Всего в очереди: {len(collection)}\n\n"
    )
    
    if source_stats:
        analytics_text += "<b>По источникам:</b>\n"
        for source, data in sorted(source_stats.items(), key=lambda x: x[1]["count"], reverse=True):
            brands_str = ", ".join(sorted(data["brands"])[:3]) if data["brands"] else "разные"
            analytics_text += f"• {source}: {data['count']} ({brands_str})\n"
        analytics_text += "\n"
    
    if brand_stats:
        analytics_text += "<b>Топ брендов:</b>\n"
        for brand, count in sorted(brand_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
            analytics_text += f"• {brand.title()}: {count}\n"
    
    # Publishing stats
    sent_count = len(state.get("sent_links", []))
    if sent_count > 0:
        analytics_text += "\n<b>Публикации:</b>\n"
        analytics_text += f"• Всего опубликовано: {sent_count}\n"
        
        # Average per day (rough estimate)
        if state.get("sent_links"):
            days_active = 30  # Assume 30 days for now
            avg_per_day = sent_count / days_active
            analytics_text += f"• Среднее в день: {avg_per_day:.1f}\n"
    
    keyboard = KeyboardBuilder.back_to_main()
    
    await update.message.reply_text(
        analytics_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


@error_handler
@admin_only
@log_action("debug command")
async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show debug information"""
    import sys
    import platform
    from telegram import __version__ as ptb_version
    from openai import __version__ as openai_version
    
    state = await get_state()
    
    debug_info = (
        "🔧 <b>Debug Information</b>\n\n"
        "<b>System:</b>\n"
        f"• Python: {sys.version.split()[0]}\n"
        f"• Platform: {platform.system()} {platform.release()}\n"
        f"• PTB: {ptb_version}\n"
        f"• OpenAI: {openai_version}\n\n"
        "<b>Bot State:</b>\n"
        f"• State file size: {len(str(state))} chars\n"
        f"• Memory usage: ~{sys.getsizeof(state) / 1024:.1f} KB\n"
        f"• Pending posts: {len(state.get('pending', {}))}\n"
        f"• Image cache: {len(state.get('generated_images', {}))}\n\n"
        "<b>Configuration:</b>\n"
        f"• Admin ID: {ADMIN_CHAT_ID}\n"
        f"• Channel: {state.get('channel', 'Not set')}\n"
        f"• Timezone: {state.get('timezone', 'UTC')}\n"
    )
    
    # Add job info
    from bot.services.scheduler import scheduler
    job_info = scheduler.get_job_info()
    if job_info:
        debug_info += "\n<b>Scheduled Jobs:</b>\n"
        for name, info in job_info.items():
            status = "✅" if info["enabled"] else "❌"
            debug_info += f"• {status} {name}\n"
    
    await update.message.reply_text(
        debug_info,
        parse_mode=ParseMode.HTML
    )


@error_handler
@admin_only
async def manage_sources_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manage news sources"""
    from config import SOURCES
    
    text = "📰 <b>Управление источниками</b>\n\n"
    
    for idx, source in enumerate(SOURCES, 1):
        status = "✅"  # In real implementation, could check if source is enabled
        text += (
            f"{status} <b>{idx}. {source['name']}</b>\n"
            f"   Тип: {source['type']}\n"
            f"   Категория: {source['category']}\n"
            f"   API: <code>{source['api'][:50]}...</code>\n\n"
        )
    
    text += "<i>Для изменения источников требуется редактирование config.py</i>"
    
    keyboard = KeyboardBuilder.back_to_main()
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


@error_handler
@admin_only
async def batch_actions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Batch actions menu"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Опубликовать все избранное", callback_data="batch_publish_favorites")],
        [InlineKeyboardButton("🗑 Удалить посты старше 7 дней", callback_data="batch_delete_old")],
        [InlineKeyboardButton("🎨 Генерировать обложки для всех", callback_data="batch_generate_covers")],
        [InlineKeyboardButton("❌ Очистить все сгенерированные", callback_data="batch_clear_generated")],
        [InlineKeyboardButton("◀️ Назад", callback_data="cmd_back_main")]
    ])
    
    await update.message.reply_text(
        "⚡️ <b>Массовые действия</b>\n\n"
        "Выберите действие для выполнения:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


@error_handler
async def handle_batch_action(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle batch action callbacks"""
    action = query.data.replace("batch_", "")
    
    if action == "publish_favorites":
        await batch_publish_favorites(query, context)
    elif action == "delete_old":
        await batch_delete_old(query, context)
    elif action == "generate_covers":
        await batch_generate_covers(query, context)
    elif action == "clear_generated":
        await batch_clear_generated(query, context)


async def batch_publish_favorites(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Publish all favorites"""
    state = await get_state()
    favorites = state.get("favorites", [])
    
    if not favorites:
        await query.edit_message_text("📭 Нет постов в избранном")
        return
    
    await query.edit_message_text(f"🚀 Публикую {len(favorites)} постов из избранного...")
    
    published = 0
    errors = 0
    
    from bot.services.publisher import publisher
    
    for fav_id in favorites[:]:  # Copy list to avoid modification during iteration
        if fav_id in state["pending"]:
            post_data = state["pending"][fav_id]
            post = Post.from_dict(post_data)
            
            success = await publisher.publish_post(context.bot, post)
            if success:
                published += 1
            else:
                errors += 1
            
            # Small delay between posts
            await asyncio.sleep(2)
    
    await query.edit_message_text(
        "✅ Массовая публикация завершена!\n\n"
        f"Опубликовано: {published}\n"
        f"Ошибок: {errors}"
    )


async def batch_delete_old(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete old posts"""
    state = await get_state()
    from bot.utils.state import clean_old_posts
    
    before_count = len(state["pending"])
    removed = await clean_old_posts(state)
    await save_state()
    
    await query.edit_message_text(
        "🗑 <b>Очистка завершена</b>\n\n"
        f"Было постов: {before_count}\n"
        f"Удалено: {removed}\n"
        f"Осталось: {len(state['pending'])}",
        parse_mode=ParseMode.HTML
    )


async def batch_generate_covers(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate covers for all posts"""
    await query.edit_message_text(
        "⚠️ Генерация обложек для всех постов может занять много времени и средств.\n"
        "Эта функция отключена в целях экономии."
    )


async def batch_clear_generated(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear all generated images"""
    state = await get_state()
    count = len(state.get("generated_images", {}))
    
    state["generated_images"] = {}
    
    # Also clear from posts
    for post_id, post_data in state["pending"].items():
        if "generated_images" in post_data:
            post_data["generated_images"] = []
    
    await save_state()
    
    await query.edit_message_text(
        f"✅ Очищено {count} сгенерированных изображений"
    )


# Monitoring functions
async def monitor_performance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Monitor bot performance"""
    import psutil
    import os
    
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        performance_text = (
            "📈 <b>Производительность бота</b>\n\n"
            "<b>Память:</b>\n"
            f"• RAM: {memory_info.rss / 1024 / 1024:.1f} MB\n"
            f"• Virtual: {memory_info.vms / 1024 / 1024:.1f} MB\n\n"
            "<b>CPU:</b>\n"
            f"• Использование: {process.cpu_percent(interval=1)}%\n"
            f"• Потоков: {process.num_threads()}\n"
        )
        
        await update.message.reply_text(
            performance_text,
            parse_mode=ParseMode.HTML
        )
        
    except ImportError:
        await update.message.reply_text(
            "📊 Для мониторинга производительности установите psutil:\n"
            "<code>pip install psutil</code>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error in monitor_performance: {e}")
        await update.message.reply_text("❌ Ошибка при получении метрик")


# Export admin handlers
admin_handlers = [
    ("broadcast", broadcast_command),
    ("export", export_command),
    ("analytics", analytics_command),
    ("debug", debug_command),
    ("sources", manage_sources_command),
    ("batch", batch_actions_command),
    ("performance", monitor_performance),
]

# Callback handlers for admin functions
admin_callback_handlers = [
    (r"^batch_", handle_batch_action),
]
