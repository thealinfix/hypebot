"""
Callback query handlers
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest

from config import ADMIN_CHAT_ID
from bot.utils.decorators import error_handler
from bot.utils.keyboards import KeyboardBuilder
from bot.utils.state import get_state, update_state, save_state
from bot.utils.time_utils import get_user_timezone, localize_datetime
from bot.utils.tags import filter_posts_by_tags, get_all_unique_tags
from bot.models.post import Post
from bot.services.publisher import publisher
from bot.services.ai_generator import ai_generator
from datetime import datetime

logger = logging.getLogger(__name__)


@error_handler
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main callback query handler"""
    query = update.callback_query
    await query.answer()
    
    try:
        data = query.data
        user_id = query.from_user.id
        
        # Check admin access for protected callbacks
        is_admin = not ADMIN_CHAT_ID or user_id == ADMIN_CHAT_ID
        
        # Route to appropriate handler
        if data.startswith("cmd_"):
            await handle_menu_commands(query, context, is_admin)
        
        elif data.startswith("settings_"):
            if not is_admin:
                await query.answer("❌ Недостаточно прав", show_alert=True)
                return
            await handle_settings(query, context)
        
        elif data.startswith("tz_"):
            if not is_admin:
                await query.answer("❌ Недостаточно прав", show_alert=True)
                return
            await handle_timezone_selection(query, context)
        
        elif data.startswith("auto_"):
            if not is_admin:
                await query.answer("❌ Недостаточно прав", show_alert=True)
                return
            await handle_auto_publish(query, context)
        
        elif data.startswith("clean_"):
            if not is_admin:
                await query.answer("❌ Недостаточно прав", show_alert=True)
                return
            await handle_clean_commands(query, context)
        
        elif data.startswith("tool_"):
            if not is_admin:
                await query.answer("❌ Недостаточно прав", show_alert=True)
                return
            await handle_tools(query, context)
        
        elif data.startswith("preview_"):
            await handle_preview_navigation(query, context)
        
        elif data.startswith("filter_"):
            await handle_filters(query, context)
        
        elif data.startswith("schedule:"):
            await handle_scheduling(query, context)
        
        elif data.startswith("toggle_fav:"):
            await handle_favorites(query, context)
        
        elif data.startswith("gen_cover"):
            await handle_generate_cover(query, context)
        
        elif data == "noop":
            return
        
        else:
            # Handle moderation actions
            if ":" in data:
                action, post_id = data.split(":", 1)
                if action in ["approve", "reject", "regen"]:
                    await handle_moderation(query, context, action, post_id)
        
    except Exception as e:
        logger.error(f"Error in callback handler: {e}", exc_info=True)
        await query.answer("❌ Произошла ошибка", show_alert=True)


async def handle_menu_commands(query, context, is_admin):
    """Handle menu navigation callbacks"""
    data = query.data
    
    if data == "cmd_status":
        await show_status_info(query)
    
    elif data == "cmd_help":
        await show_help_info(query)
    
    elif data == "cmd_preview" and is_admin:
        await start_preview_mode(query, context)
    
    elif data == "cmd_check" and is_admin:
        await query.edit_message_text("🔄 Запускаю проверку новых релизов...")
        from bot.services.scheduler import scheduler
        await scheduler.check_releases_job(context)
    
    elif data == "cmd_thoughts" and is_admin:
        await show_thoughts_prompt(query)
    
    elif data == "cmd_scheduled" and is_admin:
        await show_scheduled_posts(query)
    
    elif data == "cmd_stats":
        await show_stats_info(query)
    
    elif data == "cmd_clean_menu" and is_admin:
        await show_clean_menu(query)
    
    elif data == "cmd_tools_menu" and is_admin:
        await show_tools_menu(query)
    
    elif data == "cmd_back_main":
        await show_main_menu(query, is_admin)
    
    elif data == "cmd_auto_menu" and is_admin:
        await show_auto_publish_menu(query)
    
    elif data == "cmd_settings" and is_admin:
        await show_settings_menu(query)


async def handle_preview_navigation(query, context):
    """Handle preview navigation"""
    data = query.data
    state = await get_state()
    
    if data == "preview_close":
        await query.message.delete()
        return
    
    elif data.startswith("preview_next:") or data.startswith("preview_prev:"):
        current_idx = int(data.split(":")[1])
        preview_list = state.get("preview_mode", {}).get("list", [])
        
        if data.startswith("preview_next:"):
            new_idx = min(current_idx + 1, len(preview_list) - 1)
        else:
            new_idx = max(current_idx - 1, 0)
        
        if 0 <= new_idx < len(preview_list):
            uid = preview_list[new_idx]
            record = state["pending"].get(uid)
            if record:
                post = Post.from_dict(record)
                await send_preview(
                    context.bot,
                    post,
                    query.message.chat.id,
                    new_idx,
                    len(preview_list),
                    query.message.message_id
                )
    
    elif data.startswith("preview_full:"):
        uid = data.split(":")[1]
        record = state["pending"].get(uid)
        if record:
            post = Post.from_dict(record)
            await query.message.delete()
            await send_full_post(context.bot, post, query.message.chat.id)


async def handle_moderation(query, context, action, post_id):
    """Handle post moderation actions"""
    state = await get_state()
    record = state["pending"].get(post_id)
    
    if not record:
        await query.edit_message_text("❌ Этот пост уже был обработан")
        return
    
    post = Post.from_dict(record)
    
    if action == "approve":
        published = await publisher.publish_post(context.bot, post)
        if published:
            await query.edit_message_text(f"✅ Опубликовано: {post.title[:50]}...")
        else:
            await query.edit_message_text(f"🚨 Ошибка публикации: {post.title[:50]}...")
    
    elif action == "reject":
        await query.edit_message_text(f"❌ Пропущено: {post.title[:50]}...")
        state["pending"].pop(post_id, None)
        state["generated_images"].pop(post_id, None)
        await save_state()
    
    elif action == "regen":
        await query.edit_message_text(f"🔄 Регенерирую описание для: {post.title[:50]}...")
        
        new_description = await ai_generator.generate_caption(
            post.title,
            post.context,
            post.category
        )
        post.description = new_description
        state["pending"][post_id] = post.to_dict()
        await save_state()
        
        await publisher.send_for_moderation(context.bot, post, ADMIN_CHAT_ID)


# Menu display functions
async def show_main_menu(query, is_admin):
    """Show main menu"""
    keyboard = KeyboardBuilder.main_menu(is_admin)
    
    welcome_text = (
        "👟 <b>HypeBot</b> - мониторинг релизов кроссовок и уличной моды\n\n"
        "🔥 Актуальные релизы Nike, Adidas, Jordan и других брендов\n"
        "🤖 Автоматическая генерация описаний и обложек\n"
        "⏰ Планировщик публикаций\n"
        "⭐️ Избранное и авто-публикация\n\n"
        "Выберите нужную команду:"
    )
    
    if is_admin:
        welcome_text += "\n\n🔐 <i>Вы вошли как администратор</i>"
    
    await query.edit_message_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def show_status_info(query):
    """Show bot status"""
    state = await get_state()
    pending_count = len(state["pending"])
    sent_count = len(state["sent_links"])
    scheduled_count = len(state.get("scheduled_posts", {}))
    
    # Next scheduled post
    next_scheduled = None
    if state.get("scheduled_posts"):
        next_post = min(
            state["scheduled_posts"].items(),
            key=lambda x: x[1]["time"]
        )
        next_time = datetime.fromisoformat(next_post[1]["time"].replace('Z', '+00:00'))
        local_time = localize_datetime(next_time)
        tz = state.get("timezone", "UTC")
        next_scheduled = f"⏰ Следующий пост: {local_time.strftime('%d.%m %H:%M')} ({tz})"
    
    status_text = (
        "📊 <b>Статус бота:</b>\n\n"
        f"📝 Постов в ожидании: {pending_count}\n"
        f"⏰ Запланировано: {scheduled_count}\n"
        f"✅ Опубликовано: {sent_count}\n"
        f"📢 Канал: <code>{state.get('channel', 'Не задан')}</code>\n"
    )
    
    if next_scheduled:
        status_text += f"\n{next_scheduled}\n"
    
    keyboard = KeyboardBuilder.back_to_main()
    
    await query.edit_message_text(
        status_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def show_help_info(query):
    """Show help information"""
    help_text = (
        "ℹ️ <b>Справка по HypeBot</b>\n\n"
        "🔥 <b>Что умеет бот:</b>\n"
        "• Мониторинг релизов кроссовок и моды\n"
        "• Автоматическая генерация описаний\n"
        "• Создание обложек через ИИ\n"
        "• Планирование публикаций\n"
        "• Система тегов и фильтров\n\n"
        "📱 <b>Источники:</b>\n"
        "• SneakerNews\n"
        "• Hypebeast\n"
        "• Highsnobiety\n\n"
        "🤖 <b>ИИ функции:</b>\n"
        "• GPT-4 для генерации текстов\n"
        "• DALL-E 3 для создания обложек\n"
        "• GPT-4 Vision для анализа изображений\n\n"
        "💬 Для получения доступа администратора обратитесь к создателю бота"
    )
    
    keyboard = KeyboardBuilder.back_to_main()
    
    await query.edit_message_text(
        help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def start_preview_mode(query, context):
    """Start preview mode"""
    state = await get_state()
    
    if not state["pending"]:
        await query.edit_message_text("📭 Нет постов для просмотра")
        return
    
    # Create preview list sorted by date
    preview_list = sorted(
        state["pending"].keys(),
        key=lambda x: state["pending"][x].get("timestamp", ""),
        reverse=True
    )
    
    state["preview_mode"] = {
        "list": preview_list,
        "current": 0
    }
    await save_state()
    
    # Show first post
    first_record = state["pending"].get(preview_list[0])
    if first_record:
        post = Post.from_dict(first_record)
        await send_preview(
            context.bot,
            post,
            query.message.chat.id,
            0,
            len(preview_list),
            query.message.message_id
        )


async def show_scheduled_posts(query):
    """Show scheduled posts"""
    state = await get_state()
    scheduled = state.get("scheduled_posts", {})
    
    if not scheduled:
        text = "📭 <b>Нет запланированных постов</b>"
        keyboard = KeyboardBuilder.back_to_main()
    else:
        text = "📅 <b>Запланированные посты:</b>\n\n"
        
        for post_id, info in sorted(scheduled.items(), key=lambda x: x[1]["time"]):
            scheduled_time = datetime.fromisoformat(info["time"].replace('Z', '+00:00'))
            local_time = localize_datetime(scheduled_time)
            record = info.get("record", {})
            
            text += (
                f"⏰ {local_time.strftime('%d.%m %H:%M')} ({state.get('timezone', 'UTC')})\n"
                f"📝 {record.get('title', 'Unknown')[:50]}...\n"
                f"📍 {record.get('source', 'Unknown')}\n\n"
            )
        
        keyboard = KeyboardBuilder.back_to_main()
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def show_stats_info(query):
    """Show statistics"""
    state = await get_state()
    pending_count = len(state["pending"])
    sent_count = len(state["sent_links"])
    scheduled_count = len(state.get("scheduled_posts", {}))
    favorites_count = len(state.get("favorites", []))
    
    # Brand stats
    brand_stats = {}
    for post_data in state["pending"].values():
        post = Post.from_dict(post_data)
        for brand in post.tags.get("brands", []):
            brand_stats[brand] = brand_stats.get(brand, 0) + 1
    
    stats_text = (
        "📈 <b>Статистика бота:</b>\n\n"
        f"📝 Постов в ожидании: {pending_count}\n"
        f"⏰ Запланировано: {scheduled_count}\n"
        f"⭐️ В избранном: {favorites_count}\n"
        f"✅ Опубликовано: {sent_count}\n\n"
    )
    
    if brand_stats:
        stats_text += "🏷 <b>По брендам:</b>\n"
        for brand, count in sorted(brand_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
            stats_text += f"• {brand.title()}: {count}\n"
    
    keyboard = KeyboardBuilder.back_to_main()
    
    await query.edit_message_text(
        stats_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


# Helper functions
async def send_preview(bot, post, chat_id, current_idx, total, message_id=None):
    """Send post preview"""
    from bot.utils.time_utils import format_date_for_display
    
    state = await get_state()
    is_favorite = post.id in state.get("favorites", [])
    
    # Build preview text
    date_str = format_date_for_display(post.timestamp)
    tags_display = post.get_formatted_tags()
    
    preview_text = (
        f"📅 <b>{date_str}</b>\n"
        f"{'👟' if post.category == 'sneakers' else '👔'} <b>{post.title}</b>\n\n"
    )
    
    if tags_display:
        preview_text += f"{tags_display}\n\n"
    
    preview_text += (
        f"📍 Источник: {post.source}\n"
        f"🔗 <a href=\"{post.link}\">Ссылка на статью</a>\n"
        f"🖼 Изображений: {len(post.get_all_images())}\n"
    )
    
    if post.generated_images:
        preview_text += f"🎨 Сгенерировано: {len(post.generated_images)}\n"
    
    if is_favorite:
        preview_text += "⭐️ В избранном\n"
    
    preview_text += f"\n📊 Пост {current_idx + 1} из {total}"
    
    # Build keyboard
    keyboard = KeyboardBuilder.preview_navigation(current_idx, total, post.id, is_favorite)
    
    try:
        if message_id:
            return await bot.edit_message_text(
                preview_text,
                chat_id,
                message_id,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        else:
            return await bot.send_message(
                chat_id,
                preview_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
    except BadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            logger.error(f"Error sending preview: {e}")
    except Exception as e:
        logger.error(f"Error sending preview: {e}")


async def send_full_post(bot, post, chat_id):
    """Send full post with content"""
    loading_msg = await bot.send_message(
        chat_id,
        "⏳ Генерирую описание и загружаю полный контент...",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Parse full content if needed
        if post.needs_parsing:
            from bot.services.parser import parser_service
            post = await parser_service.parse_full_content(post)
            
            # Update in state
            state = await get_state()
            if post.id in state["pending"]:
                state["pending"][post.id] = post.to_dict()
                await save_state()
        
        # Generate description if needed
        if not post.description or post.description == post.title:
            post.description = await ai_generator.generate_caption(
                post.title,
                post.context,
                post.category
            )
            
            # Update in state
            state = await get_state()
            if post.id in state["pending"]:
                state["pending"][post.id]["description"] = post.description
                await save_state()
        
        # Delete loading message
        await bot.delete_message(chat_id, loading_msg.message_id)
        
        # Send for moderation
        await publisher.send_for_moderation(bot, post, chat_id)
        
    except Exception as e:
        logger.error(f"Error sending full post: {e}")
        await bot.edit_message_text(
            "❌ Произошла ошибка при загрузке поста",
            chat_id,
            loading_msg.message_id
        )


# Additional menu handlers
async def show_settings_menu(query):
    """Show settings menu"""
    state = await get_state()
    current_channel = state.get("channel", "Не задан")
    current_timezone = state.get("timezone", "UTC")
    
    settings_text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"📢 Канал публикации: <code>{current_channel}</code>\n"
        f"🕐 Временная зона: {current_timezone}\n"
        f"📅 Текущее время: {datetime.now(get_user_timezone()).strftime('%H:%M')}\n"
    )
    
    keyboard = KeyboardBuilder.settings_menu()
    
    await query.edit_message_text(
        settings_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def show_clean_menu(query):
    """Show cleanup menu"""
    clean_text = (
        "🧹 <b>Меню очистки</b>\n\n"
        "Выберите что нужно очистить:"
    )
    
    keyboard = KeyboardBuilder.clean_menu()
    
    await query.edit_message_text(
        clean_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def show_tools_menu(query):
    """Show tools menu"""
    tools_text = (
        "🔧 <b>Инструменты</b>\n\n"
        "Дополнительные функции для администратора:"
    )
    
    keyboard = KeyboardBuilder.tools_menu()
    
    await query.edit_message_text(
        tools_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def show_auto_publish_menu(query):
    """Show auto-publish menu"""
    state = await get_state()
    is_enabled = state.get("auto_publish", False)
    interval = state.get("publish_interval", 3600) // 60
    favorites_count = len(state.get("favorites", []))
    
    text = (
        "🤖 <b>Автоматическая публикация</b>\n\n"
        f"Статус: {'✅ Включена' if is_enabled else '❌ Выключена'}\n"
        f"Интервал: {interval} минут\n"
        f"Постов в избранном: {favorites_count}\n\n"
        "Бот будет автоматически публиковать посты из избранного с заданным интервалом"
    )
    
    keyboard = KeyboardBuilder.auto_publish_menu(is_enabled, interval)
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def show_thoughts_prompt(query):
    """Show thoughts creation prompt"""
    thoughts_text = (
        "💭 <b>Создание поста-размышления</b>\n\n"
        "Для создания личного поста используйте команду:\n"
        "<code>/thoughts описание темы</code>\n\n"
        "📝 <b>Пример:</b>\n"
        "<code>/thoughts новые Jordan 4 в черном цвете</code>\n\n"
        "📸 После команды можно прикрепить изображение для анализа\n\n"
        "💡 Бот создаст пост в личном стиле с эмоциями и впечатлениями"
    )
    
    keyboard = KeyboardBuilder.back_to_main()
    
    await query.edit_message_text(
        thoughts_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


# Settings handlers
async def handle_settings(query, context):
    """Handle settings callbacks"""
    data = query.data
    
    if data == "settings_channel":
        state = await get_state()
        state["waiting_for_channel"] = True
        await save_state()
        
        await query.edit_message_text(
            "📢 <b>Изменение канала публикации</b>\n\n"
            "Отправьте новый канал в формате:\n"
            "• <code>@channelname</code> - для публичного канала\n"
            "• <code>-1001234567890</code> - для приватного канала (ID чата)\n\n"
            f"Текущий канал: <code>{state.get('channel', 'Не задан')}</code>\n\n"
            "Или /cancel для отмены",
            parse_mode=ParseMode.HTML
        )
    
    elif data == "settings_timezone":
        await show_timezone_menu(query)


async def show_timezone_menu(query):
    """Show timezone selection"""
    keyboard = KeyboardBuilder.timezone_selection()
    
    await query.edit_message_text(
        "🕐 <b>Выберите временную зону:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def handle_timezone_selection(query, context):
    """Handle timezone selection"""
    data = query.data
    timezone_name = data.replace("tz_", "").replace("_", "/")
    
    await update_state("timezone", timezone_name)
    
    await query.edit_message_text(
        f"✅ Временная зона изменена на {timezone_name}\n\n"
        f"Текущее время: {datetime.now(get_user_timezone()).strftime('%H:%M')}",
        parse_mode=ParseMode.HTML
    )


# Other handlers
async def handle_auto_publish(query, context):
    """Handle auto-publish settings"""
    data = query.data
    
    if data == "auto_toggle":
        state = await get_state()
        state["auto_publish"] = not state.get("auto_publish", False)
        await save_state()
        await show_auto_publish_menu(query)
    
    elif data.startswith("auto_interval:"):
        interval = int(data.split(":")[1])
        await update_state("publish_interval", interval)
        await show_auto_publish_menu(query)


async def handle_clean_commands(query, context):
    """Handle cleanup commands"""
    data = query.data
    
    if data == "clean_old":
        state = await get_state()
        from bot.utils.state import clean_old_posts
        removed = await clean_old_posts(state)
        await save_state()
        
        await query.edit_message_text(
            "🗑 <b>Очистка завершена:</b>\n\n"
            f"Удалено старых постов: {removed}",
            parse_mode=ParseMode.HTML
        )
    
    elif data == "clean_pending":
        state = await get_state()
        count = len(state["pending"])
        state["pending"].clear()
        state["preview_mode"].clear()
        state["generated_images"].clear()
        await save_state()
        
        await query.edit_message_text(f"🗑 Очищено {count} постов из очереди")
    
    elif data == "clean_sent":
        state = await get_state()
        count = len(state["sent_links"])
        state["sent_links"].clear()
        await save_state()
        
        await query.edit_message_text(f"🗑 Очищен список обработанных: {count} записей")


async def handle_tools(query, context):
    """Handle tools menu"""
    data = query.data
    
    if data == "tool_test_sources":
        await query.edit_message_text("🔍 Тестирую источники...")
        
        from bot.services.parser import parser_service
        results = await parser_service.test_sources()
        
        text = "📊 <b>Результаты тестирования:</b>\n\n"
        
        for source, info in results.items():
            if info["status"] == "success":
                text += f"✅ {source}: {info.get('items_count', 0)} записей\n"
            else:
                text += f"❌ {source}: {info.get('error', 'Unknown error')}\n"
        
        keyboard = KeyboardBuilder.back_to_main()
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )


async def handle_filters(query, context):
    """Handle tag filters"""
    data = query.data
    state = await get_state()
    
    if data == "filter_tags":
        # Get all unique tags
        all_tags = get_all_unique_tags(state["pending"])
        
        keyboard = KeyboardBuilder.filter_tags(all_tags)
        
        await query.edit_message_text(
            "🏷 <b>Фильтр по тегам</b>\n\n"
            "Выберите тег для фильтрации:",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    elif data.startswith("filter_"):
        parts = data.split(":")
        if len(parts) == 2:
            filter_type = parts[0].replace("filter_", "")
            filter_value = parts[1]
            
            # Apply filter
            filtered = filter_posts_by_tags(state["pending"], filter_type, filter_value)
            
            if not filtered:
                await query.edit_message_text(f"📭 Нет постов с тегом {filter_value}")
                return
            
            # Update preview mode
            state["preview_mode"] = {
                "list": filtered,
                "current": 0,
                "filter": {filter_type: filter_value}
            }
            await save_state()
            
            await query.edit_message_text(
                f"✅ Найдено {len(filtered)} постов с тегом {filter_value}"
            )
            
            # Show first filtered post
            if filtered:
                first_record = state["pending"].get(filtered[0])
                if first_record:
                    post = Post.from_dict(first_record)
                    await send_preview(
                        context.bot,
                        post,
                        query.message.chat.id,
                        0,
                        len(filtered)
                    )
    
    elif data == "filter_reset":
        # Reset filters
        preview_list = sorted(
            state["pending"].keys(),
            key=lambda x: state["pending"][x].get("timestamp", ""),
            reverse=True
        )
        
        state["preview_mode"] = {
            "list": preview_list,
            "current": 0,
            "filter": None
        }
        await save_state()
        
        await query.edit_message_text("✅ Фильтры сброшены")
        
        if preview_list:
            first_record = state["pending"].get(preview_list[0])
            if first_record:
                post = Post.from_dict(first_record)
                await send_preview(
                    context.bot,
                    post,
                    query.message.chat.id,
                    0,
                    len(preview_list)
                )


async def handle_scheduling(query, context):
    """Handle post scheduling"""
    data = query.data
    post_id = data.split(":")[1]
    
    state = await get_state()
    state["waiting_for_schedule"] = post_id
    await save_state()
    
    user_tz = await get_user_timezone(state)
    current_time = datetime.now(user_tz).strftime('%H:%M')
    
    await query.edit_message_text(
        "⏰ <b>Планирование публикации</b>\n\n"
        f"Ваша временная зона: {state.get('timezone', 'UTC')}\n"
        f"Текущее время: {current_time}\n\n"
        "Отправьте время в одном из форматов:\n"
        "• <code>18:30</code> - сегодня в 18:30\n"
        "• <code>25.12 15:00</code> - конкретная дата\n"
        "• <code>+2h</code> - через 2 часа\n"
        "• <code>+30m</code> - через 30 минут\n"
        "• <code>+1d</code> - через 1 день\n\n"
        "Или /cancel для отмены",
        parse_mode=ParseMode.HTML
    )


async def handle_favorites(query, context):
    """Handle favorites toggle"""
    data = query.data
    post_id = data.split(":")[1]
    
    state = await get_state()
    
    if "favorites" not in state:
        state["favorites"] = []
    
    if post_id in state["favorites"]:
        state["favorites"].remove(post_id)
    else:
        state["favorites"].append(post_id)
    
    await save_state()
    
    # Update preview
    preview_list = state.get("preview_mode", {}).get("list", [])
    if post_id in preview_list:
        idx = preview_list.index(post_id)
        record = state["pending"].get(post_id)
        if record:
            post = Post.from_dict(record)
            await send_preview(
                context.bot,
                post,
                query.message.chat.id,
                idx,
                len(preview_list),
                query.message.message_id
            )


async def handle_generate_cover(query, context):
    """Handle cover generation"""
    data = query.data
    post_id = data.split(":")[-1]
    
    state = await get_state()
    record = state["pending"].get(post_id)
    
    if not record:
        await query.answer("Пост не найден", show_alert=True)
        return
    
    post = Post.from_dict(record)
    
    await query.edit_message_text("🎨 Генерирую обложку...")
    
    # Generate image
    image_url = await ai_generator.generate_custom_image(
        post.title,
        post.category
    )
    
    if image_url:
        # Save generated image
        post.add_generated_image(image_url)
        state["pending"][post_id] = post.to_dict()
        
        if post_id not in state["generated_images"]:
            state["generated_images"][post_id] = []
        state["generated_images"][post_id].append(image_url)
        
        await save_state()
        
        await query.edit_message_text("✅ Обложка сгенерирована!")
        
        # Show updated post
        if "full" in data:
            await publisher.send_for_moderation(context.bot, post, query.message.chat.id)
    else:
        await query.edit_message_text("❌ Ошибка при генерации обложки")


# Export callback handler for registration
callback_handlers = [
    callback_handler
]
