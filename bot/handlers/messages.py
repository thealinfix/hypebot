"""
Message handlers for text and media
"""
import logging
from telegram import Update, PhotoSize
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import ADMIN_CHAT_ID
from bot.utils.decorators import error_handler, log_action
from bot.utils.state import get_state, update_state, save_state, reset_state
from bot.utils.time_utils import parse_schedule_time, get_user_timezone, localize_datetime
from bot.utils.helpers import validate_channel_format
from bot.utils.keyboards import KeyboardBuilder
from bot.models.post import Post
from bot.services.ai_generator import ai_generator
from bot.services.publisher import publisher

logger = logging.getLogger(__name__)


@error_handler
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all text messages"""
    user_id = update.effective_user.id
    if ADMIN_CHAT_ID and user_id != ADMIN_CHAT_ID:
        return
    
    text = update.message.text.strip()
    state = await get_state()
    
    # Check various waiting states
    if state.get("waiting_for_channel"):
        await handle_channel_input(update, context, text)
    
    elif state.get("waiting_for_schedule"):
        await handle_schedule_input(update, context, text)
    
    elif state.get("editing_schedule"):
        await handle_schedule_edit(update, context, text)
    
    elif state.get("waiting_for_prompt"):
        await handle_custom_prompt(update, context, text)
    
    elif state.get("auto_interval_custom"):
        await handle_custom_interval(update, context, text)
    
    else:
        # No specific waiting state - could be a mistyped command
        if text.startswith("/"):
            await update.message.reply_text(
                "❌ Неизвестная команда. Используйте /help для справки"
            )


@error_handler
@log_action("photo message")
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages"""
    state = await get_state()
    
    if not state.get("waiting_for_image"):
        return
    
    user_id = update.effective_user.id
    if ADMIN_CHAT_ID and user_id != ADMIN_CHAT_ID:
        return
    
    waiting_data = state["waiting_for_image"]
    state["waiting_for_image"] = None
    await save_state()
    
    # Show processing
    msg = await update.message.reply_text("🔍 Анализирую изображение...")
    
    try:
        # Get photo
        photo: PhotoSize = update.message.photo[-1]  # Get largest size
        file = await context.bot.get_file(photo.file_id)
        
        # Download image
        image_bytes = await file.download_as_bytearray()
        
        # Analyze image
        image_description = await ai_generator.analyze_image(bytes(image_bytes))
        
        if waiting_data["type"] == "thoughts":
            await generate_thought_with_image(
                update, context, waiting_data, 
                photo.file_id, image_description, msg
            )
        
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await msg.edit_text("❌ Ошибка при обработке изображения")


async def handle_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle channel input"""
    new_channel = text.strip()
    
    # Validate channel format
    if validate_channel_format(new_channel):
        await update_state("channel", new_channel)
        state = await get_state()
        state["waiting_for_channel"] = False
        await save_state()
        
        await update.message.reply_text(
            f"✅ Канал изменен на: <code>{new_channel}</code>\n\n"
            "Все новые публикации будут отправляться в этот канал.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            "❌ Неверный формат канала\n\n"
            "Используйте:\n"
            "• <code>@channelname</code> для публичного канала\n"
            "• <code>-1001234567890</code> для приватного канала",
            parse_mode=ParseMode.HTML
        )


async def handle_schedule_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle schedule time input"""
    state = await get_state()
    post_id = state["waiting_for_schedule"]
    
    user_tz = await get_user_timezone(state)
    scheduled_time = parse_schedule_time(text, user_tz)
    
    if scheduled_time:
        record = state["pending"].get(post_id)
        
        if record:
            # Save scheduled post
            state["scheduled_posts"][post_id] = {
                "time": scheduled_time.isoformat(),
                "record": record
            }
            
            state["waiting_for_schedule"] = None
            await save_state()
            
            local_time = localize_datetime(scheduled_time, user_tz)
            await update.message.reply_text(
                f"✅ Пост запланирован на {local_time.strftime('%d.%m.%Y %H:%M')} "
                f"({state.get('timezone', 'UTC')})\n"
                f"📝 {record['title'][:50]}..."
            )
        else:
            await update.message.reply_text("❌ Пост не найден")
    else:
        await update.message.reply_text(
            "❌ Неверный формат времени\n\n"
            "Используйте:\n"
            "• <code>18:30</code>\n"
            "• <code>25.12 15:00</code>\n"
            "• <code>+2h</code>",
            parse_mode=ParseMode.HTML
        )


async def handle_schedule_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle schedule edit"""
    state = await get_state()
    post_id = state["editing_schedule"]
    
    user_tz = await get_user_timezone(state)
    scheduled_time = parse_schedule_time(text, user_tz)
    
    if scheduled_time:
        if post_id in state.get("scheduled_posts", {}):
            state["scheduled_posts"][post_id]["time"] = scheduled_time.isoformat()
            state["editing_schedule"] = None
            await save_state()
            
            local_time = localize_datetime(scheduled_time, user_tz)
            await update.message.reply_text(
                f"✅ Время изменено на {local_time.strftime('%d.%m.%Y %H:%M')} "
                f"({state.get('timezone', 'UTC')})"
            )
        else:
            await update.message.reply_text("❌ Запланированный пост не найден")
    else:
        await update.message.reply_text("❌ Неверный формат времени")


async def handle_custom_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle custom image prompt"""
    state = await get_state()
    post_id = state["waiting_for_prompt"]
    record = state["pending"].get(post_id)
    
    if record:
        await update.message.reply_text("🎨 Генерирую изображение с вашим описанием...")
        
        post = Post.from_dict(record)
        
        # Generate image
        image_url = await ai_generator.generate_image(text, "creative")
        
        if image_url:
            # Save generated image
            post.add_generated_image(image_url)
            
            if post_id not in state["generated_images"]:
                state["generated_images"][post_id] = []
            
            state["generated_images"][post_id].append(image_url)
            state["pending"][post_id] = post.to_dict()
            state["waiting_for_prompt"] = None
            await save_state()
            
            await update.message.reply_text("✅ Изображение сгенерировано!")
            
            # Send for moderation
            await publisher.send_for_moderation(
                context.bot, post, update.effective_chat.id
            )
        else:
            await update.message.reply_text("❌ Ошибка при генерации изображения")
    else:
        await update.message.reply_text("❌ Пост не найден")
        state["waiting_for_prompt"] = None
        await save_state()


async def handle_custom_interval(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle custom auto-publish interval"""
    try:
        minutes = int(text)
        if 10 <= minutes <= 1440:  # 10 min to 24 hours
            await update_state("publish_interval", minutes * 60)
            state = await get_state()
            state["auto_interval_custom"] = False
            await save_state()
            
            await update.message.reply_text(f"✅ Интервал установлен: {minutes} минут")
        else:
            await update.message.reply_text("❌ Интервал должен быть от 10 до 1440 минут")
    except ValueError:
        await update.message.reply_text("❌ Введите число минут")


async def generate_thought_with_image(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                    waiting_data: dict, file_id: str, 
                                    image_description: str, loading_msg):
    """Generate thought post with image"""
    try:
        await loading_msg.edit_text("💭 Генерирую мысли на основе изображения...")
        
        # Generate thought
        thought_text = await ai_generator.generate_caption(
            waiting_data["topic"],
            "",
            "sneakers",
            is_thought=True,
            image_description=image_description
        )
        
        # Add hashtags
        from bot.utils.tags import get_hashtags
        hashtags = get_hashtags(waiting_data["topic"], "sneakers")
        final_text = f"{thought_text}\n\n{hashtags}"
        
        # Build keyboard
        keyboard = KeyboardBuilder.thoughts_actions(has_image=True)
        
        # Save thought data
        state = await get_state()
        state["current_thought"] = {
            "text": final_text,
            "topic": waiting_data["topic"],
            "image_description": image_description,
            "image_url": file_id
        }
        await save_state()
        
        await loading_msg.edit_text(
            f"💭 <b>Пост-размышление:</b>\n\n{final_text}\n\n"
            "📸 Изображение прикреплено",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error generating thought with image: {e}")
        await loading_msg.edit_text("❌ Ошибка при генерации мыслей")


async def generate_thought_without_image(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                       waiting_data: dict):
    """Generate thought post without image"""
    msg = await update.message.reply_text("💭 Генерирую мысли...")
    
    try:
        # Generate thought
        thought_text = await ai_generator.generate_caption(
            waiting_data["topic"],
            "",
            "sneakers",
            is_thought=True
        )
        
        # Add hashtags
        from bot.utils.tags import get_hashtags
        hashtags = get_hashtags(waiting_data["topic"], "sneakers")
        final_text = f"{thought_text}\n\n{hashtags}"
        
        # Build keyboard
        keyboard = KeyboardBuilder.thoughts_actions(has_image=False)
        
        # Save thought data
        state = await get_state()
        state["current_thought"] = {
            "text": final_text,
            "topic": waiting_data["topic"]
        }
        await save_state()
        
        await msg.edit_text(
            f"💭 <b>Пост-размышление:</b>\n\n{final_text}",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error generating thought: {e}")
        await msg.edit_text("❌ Ошибка при генерации мыслей")


@error_handler
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document uploads"""
    user_id = update.effective_user.id
    if ADMIN_CHAT_ID and user_id != ADMIN_CHAT_ID:
        return
    
    document = update.message.document
    
    # Check if it's an image document
    if document.mime_type and document.mime_type.startswith("image/"):
        # Treat as photo
        state = await get_state()
        if state.get("waiting_for_image"):
            await update.message.reply_text(
                "📎 Получен документ-изображение. Обрабатываю..."
            )
            
            # Create fake photo update
            class FakePhoto:
                def __init__(self, file_id):
                    self.file_id = file_id
            
            update.message.photo = [FakePhoto(document.file_id)]
            await handle_photo(update, context)
        else:
            await update.message.reply_text(
                "📎 Получено изображение. Используйте /thoughts для создания поста"
            )
    else:
        await update.message.reply_text(
            "📎 Неподдерживаемый тип файла"
        )


@error_handler  
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages"""
    user_id = update.effective_user.id
    if ADMIN_CHAT_ID and user_id != ADMIN_CHAT_ID:
        return
    
    await update.message.reply_text(
        "🎤 Голосовые сообщения пока не поддерживаются.\n"
        "Используйте текстовые команды или /help для справки"
    )


@error_handler
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle video messages"""
    user_id = update.effective_user.id
    if ADMIN_CHAT_ID and user_id != ADMIN_CHAT_ID:
        return
    
    await update.message.reply_text(
        "📹 Видео пока не поддерживаются.\n"
        "Используйте фото для создания постов"
    )


@error_handler
async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle sticker messages"""
    user_id = update.effective_user.id
    if ADMIN_CHAT_ID and user_id != ADMIN_CHAT_ID:
        return
    
    # Fun response to stickers
    sticker = update.message.sticker
    if sticker.emoji:
        await update.message.reply_text(f"{sticker.emoji} Классный стикер!")
    else:
        await update.message.reply_text("👍 Спасибо за стикер!")


# Special handlers for callback data in messages
async def handle_reset_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                  confirmed: bool) -> None:
    """Handle reset state confirmation"""
    if confirmed:
        await reset_state()
        await update.message.reply_text(
            "✅ Состояние бота сброшено!\n\n"
            "Все посты очищены. Запустите /check для поиска новых релизов."
        )
    else:
        await update.message.reply_text("❌ Сброс отменен")


# Export handlers for registration
message_handlers = [
    ("text", handle_text_message),
    ("photo", handle_photo),
    ("document", handle_document),
    ("voice", handle_voice), 
    ("video", handle_video),
    ("sticker", handle_sticker),
]
