"""
Decorators for bot handlers
"""
import functools
import logging
from typing import Callable
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def admin_only(func: Callable) -> Callable:
    """Decorator to restrict access to admin only"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from config import ADMIN_CHAT_ID
        
        # Get user ID from update
        user_id = None
        if update.message:
            user_id = update.message.from_user.id
        elif update.callback_query:
            user_id = update.callback_query.from_user.id
        
        # Check admin access
        if not ADMIN_CHAT_ID or user_id == ADMIN_CHAT_ID:
            return await func(update, context, *args, **kwargs)
        else:
            if update.message:
                await update.message.reply_text("❌ Эта команда доступна только администратору")
            elif update.callback_query:
                await update.callback_query.answer("❌ Недостаточно прав", show_alert=True)
            return None
    
    return wrapper


def log_action(action: str) -> Callable:
    """Decorator to log user actions"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = None
            if update.message:
                user = update.message.from_user
            elif update.callback_query:
                user = update.callback_query.from_user
            
            user_info = f"{user.username or user.first_name} ({user.id})" if user else "Unknown"
            logger.info(f"{action} by {user_info}")
            
            try:
                result = await func(update, context, *args, **kwargs)
                logger.info(f"{action} completed successfully")
                return result
            except Exception as e:
                logger.error(f"{action} failed: {e}", exc_info=True)
                raise
        
        return wrapper
    return decorator


def error_handler(func: Callable) -> Callable:
    """Decorator to handle errors in handlers"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            
            error_message = "❌ Произошла ошибка при выполнении команды"
            
            if update.message:
                await update.message.reply_text(error_message)
            elif update.callback_query:
                await update.callback_query.answer(error_message, show_alert=True)
                try:
                    await update.callback_query.edit_message_text(error_message)
                except:
                    pass
    
    return wrapper


def typing_action(func: Callable) -> Callable:
    """Decorator to show typing action"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.message:
            await update.message.chat.send_action("typing")
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def rate_limit(calls: int = 3, period: int = 60) -> Callable:
    """Rate limiting decorator"""
    def decorator(func: Callable) -> Callable:
        call_times = {}
        
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            import time
            
            # Get user ID
            user_id = None
            if update.message:
                user_id = update.message.from_user.id
            elif update.callback_query:
                user_id = update.callback_query.from_user.id
            
            if not user_id:
                return await func(update, context, *args, **kwargs)
            
            # Check rate limit
            current_time = time.time()
            user_calls = call_times.get(user_id, [])
            
            # Remove old calls
            user_calls = [t for t in user_calls if current_time - t < period]
            
            if len(user_calls) >= calls:
                remaining = int(period - (current_time - user_calls[0]))
                
                message = f"⏳ Слишком много запросов. Попробуйте через {remaining} сек."
                
                if update.message:
                    await update.message.reply_text(message)
                elif update.callback_query:
                    await update.callback_query.answer(message, show_alert=True)
                
                return None
            
            # Add current call
            user_calls.append(current_time)
            call_times[user_id] = user_calls
            
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator


def callback_data_handler(prefix: str) -> Callable:
    """Decorator to handle callback data with specific prefix"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if not update.callback_query:
                return
            
            data = update.callback_query.data
            if not data or not data.startswith(prefix):
                return
            
            # Extract data after prefix
            action_data = data[len(prefix):]
            return await func(update, context, action_data, *args, **kwargs)
        
        return wrapper
    return decorator
