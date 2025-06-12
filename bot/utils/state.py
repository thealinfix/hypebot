"""
State management module with optimizations
"""
import json
import asyncio
import aiofiles
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from config import STATE_FILE, MAX_POST_AGE_DAYS, MAX_PENDING_POSTS, DEFAULT_TIMEZONE, TELEGRAM_CHANNEL

logger = logging.getLogger(__name__)

# Global state with thread-safe access
_state: Dict[str, Any] = {}
_state_lock = asyncio.Lock()


async def get_default_state() -> Dict[str, Any]:
    """Get default state structure"""
    return {
        "sent_links": [],
        "pending": {},
        "moderation_queue": [],
        "preview_mode": {},
        "thoughts_mode": False,
        "scheduled_posts": {},
        "generated_images": {},
        "waiting_for_image": None,
        "current_thought": None,
        "waiting_for_schedule": None,
        "editing_schedule": None,
        "favorites": [],
        "auto_publish": False,
        "publish_interval": 3600,
        "timezone": DEFAULT_TIMEZONE,
        "channel": TELEGRAM_CHANNEL,
        "waiting_for_channel": False,
        "waiting_for_prompt": None,
        "auto_interval_custom": False,
        "last_auto_publish": None
    }


async def clean_old_posts(state_dict: Dict[str, Any]) -> int:
    """Clean old posts from queue"""
    now = datetime.now(timezone.utc)
    removed_count = 0
    
    # Remove old posts
    for uid in list(state_dict["pending"].keys()):
        post = state_dict["pending"][uid]
        try:
            post_date = datetime.fromisoformat(post.get("timestamp", "").replace('Z', '+00:00'))
            age = now - post_date
            
            if age.days > MAX_POST_AGE_DAYS:
                del state_dict["pending"][uid]
                removed_count += 1
        except Exception as e:
            logger.error(f"Error checking post age: {e}")
            continue
    
    # Limit number of posts
    if len(state_dict["pending"]) > MAX_PENDING_POSTS:
        sorted_posts = sorted(
            state_dict["pending"].items(),
            key=lambda x: x[1].get("timestamp", ""),
            reverse=True
        )
        
        state_dict["pending"] = dict(sorted_posts[:MAX_PENDING_POSTS])
        removed_count += len(sorted_posts) - MAX_PENDING_POSTS
    
    if removed_count > 0:
        logger.info(f"Removed {removed_count} old posts")
    
    return removed_count


async def load_state() -> Dict[str, Any]:
    """Load state from file asynchronously"""
    global _state
    
    try:
        if STATE_FILE.exists():
            async with aiofiles.open(STATE_FILE, "r", encoding="utf-8") as f:
                content = await f.read()
                loaded_state = json.loads(content)
        else:
            loaded_state = await get_default_state()
            
        # Merge with defaults
        default_state = await get_default_state()
        for key, default_value in default_state.items():
            if key not in loaded_state:
                loaded_state[key] = default_value
        
        # Validate pending entries
        valid_pending = {}
        for uid, record in loaded_state["pending"].items():
            if isinstance(record, dict) and all(key in record for key in ['id', 'title', 'link']):
                valid_pending[uid] = record
            else:
                logger.warning(f"Removing invalid pending entry: {uid}")
        loaded_state["pending"] = valid_pending
        
        # Clean old posts
        await clean_old_posts(loaded_state)
        
        logger.info("State loaded successfully")
        return loaded_state
        
    except Exception as e:
        logger.error(f"Error loading state: {e}")
        return await get_default_state()


async def save_state() -> None:
    """Save state to file asynchronously"""
    global _state
    
    async with _state_lock:
        try:
            # Ensure directory exists
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Save atomically
            temp_file = STATE_FILE.with_suffix('.tmp')
            async with aiofiles.open(temp_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(_state, ensure_ascii=False, indent=2))
            
            # Rename atomically
            temp_file.replace(STATE_FILE)
            
            logger.debug("State saved successfully")
        except Exception as e:
            logger.error(f"Error saving state: {e}")


def initialize_state() -> None:
    """Initialize global state synchronously"""
    global _state
    # Run async load in sync context
    loop = asyncio.new_event_loop()
    _state = loop.run_until_complete(load_state())
    loop.close()
    logger.info("State initialized")


async def get_state() -> Dict[str, Any]:
    """Get current state with thread safety"""
    async with _state_lock:
        return _state.copy()


async def update_state(key: str, value: Any) -> None:
    """Update state value and save"""
    async with _state_lock:
        _state[key] = value
    await save_state()


async def update_state_partial(updates: Dict[str, Any]) -> None:
    """Update multiple state values at once"""
    async with _state_lock:
        _state.update(updates)
    await save_state()


async def get_state_value(key: str, default: Any = None) -> Any:
    """Get specific state value"""
    async with _state_lock:
        return _state.get(key, default)


async def reset_state() -> None:
    """Reset state to defaults"""
    global _state
    async with _state_lock:
        _state = await get_default_state()
    await save_state()
    logger.info("State reset to defaults")


# Synchronous wrapper for compatibility
def get_state_sync() -> Dict[str, Any]:
    """Synchronous state getter for legacy code"""
    return _state.copy()


def save_state_sync() -> None:
    """Synchronous state saver for legacy code"""
    loop = asyncio.new_event_loop()
    loop.run_until_complete(save_state())
    loop.close()
