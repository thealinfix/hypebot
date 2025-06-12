"""
Command handlers for bot
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import ADMIN_CHAT_ID
from bot.utils.decorators import admin_only, error_handler, log_action, typing_action
from bot.utils.keyboards import KeyboardBuilder
from bot.utils.state import get_state, save_state
from bot.services.scheduler import scheduler

logger = logging.getLogger(__name__)


@error_handler
@log_action("start command")
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user = update.effective_user
    is_admin = not ADMIN_CHAT_ID or user.id == ADMIN_CHAT_ID
    
    # Build keyboard
    keyboard = KeyboardBuilder.main_menu(is_admin)
    
    # Build welcome message
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
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


@error_handler
@admin_only
@log_action("preview command")
async def preview_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /preview command"""
    from bot.handlers.callbacks import start_preview_mode
    
    # Create fake callback query
    class FakeQuery:
        def __init__(self, message, user):
            self.message = message
            self.from_user = user
            self.data = "cmd_preview"
        
        async def answer(self):
            pass
        
        async def edit_message_text(self, *args, **kwargs):
            await self.message.edit_text(*args, **kwargs)
    
    fake_query = FakeQuery(update.message, update.effective_user)
    await start_preview_mode(fake_query, context)


@error_handler
@admin_only
@log_action("check command")
@typing_action
async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /check command"""
    await update.message.reply_text("🔄 Запускаю проверку новых релизов...")
    
    # Run check job
    from bot.services.scheduler import scheduler
    await scheduler.check_releases_job(context)


@error_handler
@admin_only
@log_action("thoughts command")
async def thoughts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /thoughts command"""
    # Check arguments
    if not context.args:
        await update.message.reply_text(
            "💭 Использование команды:\n"
            "/thoughts <краткое описание>\n\n"
            "Пример:\n"
            "/thoughts новые Jordan 4 в черном цвете\n\n"
            "Также можно прикрепить изображение!"
        )
        return
    
    # Get topic
    topic = " ".join(context.args)
    
    # Save in state for waiting image
    state = await get_state()
    state["waiting_for_image"] = {
        "type": "thoughts",
        "topic": topic,
        "message_id": update.message.message_id
    }
    await save_state()
    
    # Show process
    await update.message.reply_text(
        "💭 Отправьте изображение для анализа или нажмите /skip чтобы создать пост без изображения"
    )


@error_handler
async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /skip command"""
    state = await get_state()
    
    if not state.get("waiting_for_image"):
        await update.message.reply_text("❌ Нечего пропускать")
        return
    
    waiting_data = state["waiting_for_image"]
    state["waiting_for_image"] = None
    await save_state()
    
    if waiting_data["type"] == "thoughts":
        # Generate thoughts without image
        from bot.handlers.messages import generate_thought_without_image
        await generate_thought_without_image(update, context, waiting_data)


@error_handler
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command"""
    user_id = update.effective_user.id
    if ADMIN_CHAT_ID and user_id != ADMIN_CHAT_ID:
        return
    
    state = await get_state()
    cancelled = []
    
    # Check all waiting states
    if state.get("waiting_for_schedule"):
        state["waiting_for_schedule"] = None
        cancelled.append("планирование поста")
    
    if state.get("editing_schedule"):
        state["editing_schedule"] = None
        cancelled.append("изменение расписания")
    
    if state.get("waiting_for_image"):
        state["waiting_for_image"] = None
        cancelled.append("ожидание изображения")
    
    if state.get("waiting_for_prompt"):
        state["waiting_for_prompt"] = None
        cancelled.append("ожидание промпта")
    
    if state.get("auto_interval_custom"):
        state["auto_interval_custom"] = False
        cancelled.append("установка интервала")
    
    if state.get("waiting_for_channel"):
        state["waiting_for_channel"] = False
        cancelled.append("изменение канала")
    
    await save_state()
    
    if cancelled:
        await update.message.reply_text(f"❌ Отменено: {', '.join(cancelled)}")
    else:
        await update.message.reply_text("❌ Нечего отменять")


@error_handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    help_text = (
        "ℹ️ <b>Справка по HypeBot</b>\n\n"
        "🔥 <b>Доступные команды:</b>\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n"
        "/cancel - Отменить текущую операцию\n"
    )
    
    user_id = update.effective_user.id
    if not ADMIN_CHAT_ID or user_id == ADMIN_CHAT_ID:
        help_text += (
            "\n<b>Команды администратора:</b>\n"
            "/preview - Просмотр постов в очереди\n"
            "/check - Проверить новые релизы\n"
            "/thoughts - Создать пост-размышление\n"
            "/scheduled - Показать запланированные\n"
            "/stats - Статистика бота\n"
            "/reset_state - Сброс состояния (опасно!)\n"
        )
    
    help_text += (
        "\n\n📱 <b>Источники:</b>\n"
        "• SneakerNews\n"
        "• Hypebeast\n"
        "• Highsnobiety\n"
        "\n🤖 <b>ИИ функции:</b>\n"
        "• GPT-4 для генерации текстов\n"
        "• DALL-E 3 для создания обложек\n"
        "• GPT-4 Vision для анализа изображений"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.HTML
    )


@error_handler
@admin_only
@log_action("scheduled command")
async def scheduled_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /scheduled command"""
    from bot.handlers.callbacks import show_scheduled_posts
    
    # Create fake callback query
    class FakeQuery:
        def __init__(self, message, user):
            self.message = message
            self.from_user = user
            self.data = "cmd_scheduled"
        
        async def answer(self):
            pass
        
        async def edit_message_text(self, *args, **kwargs):
            await self.message.reply_text(*args, **kwargs)
    
    fake_query = FakeQuery(update.message, update.effective_user)
    await show_scheduled_posts(fake_query)


@error_handler
@admin_only
@log_action("stats command")
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command"""
    from bot.handlers.callbacks import show_stats_info
    
    # Create fake callback query
    class FakeQuery:
        def __init__(self, message, user):
            self.message = message
            self.from_user = user
            self.data = "cmd_stats"
        
        async def answer(self):
            pass
        
        async def edit_message_text(self, *args, **kwargs):
            await self.message.reply_text(*args, **kwargs)
    
    fake_query = FakeQuery(update.message, update.effective_user)
    await show_stats_info(fake_query)


@error_handler
@admin_only
@log_action("reset_state command")
async def reset_state_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reset_state command"""
    # Ask for confirmation
    keyboard = KeyboardBuilder.yes_no("reset_state")
    
    await update.message.reply_text(
        "⚠️ <b>Внимание!</b>\n\n"
        "Вы действительно хотите сбросить состояние бота?\n"
        "Это удалит ВСЕ посты, настройки и данные!\n\n"
        "Подтвердите действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


@error_handler
@admin_only
async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /test command (hidden)"""
    # Test various bot functions
    state = await get_state()
    
    info = (
        "🔧 <b>Отладочная информация</b>\n\n"
        f"📝 Постов в очереди: {len(state.get('pending', {}))}\n"
        f"⏰ Запланировано: {len(state.get('scheduled_posts', {}))}\n"
        f"⭐️ В избранном: {len(state.get('favorites', []))}\n"
        f"✅ Опубликовано: {len(state.get('sent_links', []))}\n"
        f"🤖 Авто-публикация: {'Вкл' if state.get('auto_publish') else 'Выкл'}\n"
        f"📢 Канал: <code>{state.get('channel', 'Не задан')}</code>\n"
        f"🕐 Часовой пояс: {state.get('timezone', 'UTC')}\n"
    )
    
    # Get job info
    job_info = scheduler.get_job_info()
    info += "\n<b>Задачи планировщика:</b>\n"
    for name, data in job_info.items():
        status = "✅" if data["enabled"] else "❌"
        info += f"{status} {name}"
        if data["next_run"]:
            info += f" (след. запуск: {data['next_run'][:16]})"
        info += "\n"
    
    await update.message.reply_text(info, parse_mode=ParseMode.HTML)


# Export handlers for registration
command_handlers = [
    ("start", start_command),
    ("help", help_command),
    ("cancel", cancel_command),
    ("skip", skip_command),
    ("preview", preview_command),
    ("check", check_command),
    ("thoughts", thoughts_command),
    ("scheduled", scheduled_command),
    ("stats", stats_command),
    ("reset_state", reset_state_command),
    ("test", test_command),
]
