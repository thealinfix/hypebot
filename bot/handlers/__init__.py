"""
Handler registration module
"""
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from bot.handlers.commands import command_handlers
from bot.handlers.callbacks import callback_handlers
from bot.handlers.messages import message_handlers
from bot.handlers.admin import admin_handlers, admin_callback_handlers

logger = logging.getLogger(__name__)


def setup_handlers(application: Application) -> None:
    """Register all handlers with the application"""
    logger.info("Setting up handlers...")
    
    # Command handlers
    for command_name, handler_func in command_handlers:
        application.add_handler(CommandHandler(command_name, handler_func))
        logger.debug(f"Registered command: /{command_name}")
    
    # Admin command handlers
    for command_name, handler_func in admin_handlers:
        application.add_handler(CommandHandler(command_name, handler_func))
        logger.debug(f"Registered admin command: /{command_name}")
    
    # Message handlers
    for message_type, handler_func in message_handlers:
        if message_type == "text":
            application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND, 
                handler_func
            ))
        elif message_type == "photo":
            application.add_handler(MessageHandler(filters.PHOTO, handler_func))
        elif message_type == "document":
            application.add_handler(MessageHandler(filters.Document.ALL, handler_func))
        elif message_type == "voice":
            application.add_handler(MessageHandler(filters.VOICE, handler_func))
        elif message_type == "video":
            application.add_handler(MessageHandler(filters.VIDEO, handler_func))
        elif message_type == "sticker":
            application.add_handler(MessageHandler(filters.Sticker.ALL, handler_func))
        
        logger.debug(f"Registered message handler: {message_type}")
    
    # Callback query handlers
    for handler_func in callback_handlers:
        application.add_handler(CallbackQueryHandler(handler_func))
    logger.debug("Registered callback query handler")
    
    # Admin callback handlers with patterns
    for pattern, handler_func in admin_callback_handlers:
        application.add_handler(CallbackQueryHandler(handler_func, pattern=pattern))
        logger.debug(f"Registered admin callback handler: {pattern}")
    
    logger.info(f"Handler setup complete. Total handlers: "
                f"{len(command_handlers) + len(admin_handlers)} commands, "
                f"{len(message_handlers)} message types, "
                f"{len(callback_handlers) + len(admin_callback_handlers)} callbacks")


# Error handler
async def error_handler(update, context):
    """Log errors caused by updates"""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    
    # Notify admin about errors
    try:
        from config import ADMIN_CHAT_ID
        if ADMIN_CHAT_ID and update and update.effective_user:
            error_message = (
                f"⚠️ Произошла ошибка:\n"
                f"User: {update.effective_user.id}\n"
                f"Error: {type(context.error).__name__}: {str(context.error)}"
            )
            await context.bot.send_message(ADMIN_CHAT_ID, error_message)
    except:
        pass
