#!/usr/bin/env python3
"""
HypeBot - Sneaker and Fashion Release Monitor
"""
import signal
import sys

from telegram.ext import Application
from telegram.error import Conflict

from config import (
    TELEGRAM_TOKEN, 
    LOG_LEVEL, 
    LOG_FILE,
    validate_config
)
from bot.handlers import setup_handlers
from bot.services.scheduler import setup_jobs
from bot.utils.state import initialize_state
from bot.utils.logger import setup_logging

# Setup logging
logger = setup_logging(LOG_LEVEL, LOG_FILE)


async def startup(application: Application) -> None:
    """Initialize bot on startup"""
    logger.info("Starting HypeBot...")
    
    # Initialize state
    initialize_state()
    
    # Setup jobs
    setup_jobs(application)
    
    logger.info("HypeBot started successfully")


async def shutdown(application: Application) -> None:
    """Cleanup on shutdown"""
    logger.info("Shutting down HypeBot...")
    
    # Save state
    from bot.utils.state import save_state
    save_state()
    
    logger.info("HypeBot stopped")


def handle_signal(signum, frame):
    """Handle system signals"""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


def main():
    """Main entry point"""
    try:
        # Validate configuration
        validate_config()
        
        # Create application
        app = Application.builder() \
            .token(TELEGRAM_TOKEN) \
            .connect_timeout(30) \
            .read_timeout(30) \
            .post_init(startup) \
            .post_shutdown(shutdown) \
            .build()
        
        # Setup handlers
        setup_handlers(app)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
        
        # Run bot
        logger.info("Starting polling...")
        app.run_polling(drop_pending_updates=True)
        
    except Conflict:
        logger.critical("Bot is already running in another process")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
