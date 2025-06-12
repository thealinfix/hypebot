# AI Development Guide - HypeBot Continuation

## Quick Context for AI Assistant

When continuing development on this bot, provide this context: I'm working on HypeBot - a modular Python Telegram bot for sneaker/fashion monitoring.
Tech: Python 3.10+, python-telegram-bot, OpenAI API, asyncio
Architecture: Modular with handlers/, services/, utils/, models/
Current state: [describe what you want to do] ## Project Structure
- `main.py` - Entry point
- `config.py` - Configuration
- `bot/handlers/` - User interaction
- `bot/services/` - Business logic
- `bot/utils/` - Helpers
- `bot/models/` - Data models

## Key Patterns
- Async/await everywhere
- Decorators: @admin_only, @error_handler
- Singleton services
- JSON state management
- Module logging

## To Add New Features
1. Create handler in bot/handlers/
2. Create service in bot/services/ if needed
3. Register in bot/handlers/__init__.py
4. Update keyboards if needed

## Common Improvements
- Add database support (SQLAlchemy)
- Add web interface (FastAPI)
- Add more sources
- Enhance AI prompts
- Add tests
