# HypeBot - AI Assistant Context

## Quick Start for New AI Session

If you need to continue working on this bot in a new session, use this message:

I have a modular Python Telegram bot project called HypeBot for sneaker/fashion monitoring.
Location: ~/hypebot/
Structure: 24+ Python modules organized in bot/{handlers,services,utils,models}/
Tech: Python 3.10+, python-telegram-bot, OpenAI API, asyncio

Current task: [describe what you need]

The bot is fully functional with these features:
- RSS/API parsing from multiple sources
- AI content generation (GPT-4, DALL-E 3)
- Post scheduling and moderation
- Tag extraction and filtering
- Auto-publishing from favorites

All code follows async/await patterns with proper error handling.

## Project Structure Summary

hypebot/
├── main.py                 # Entry point
├── config.py              # All configuration
├── bot/
│   ├── handlers/          # User interaction (5 files)
│   ├── services/          # Business logic (5 files)
│   ├── utils/             # Utilities (8 files)
│   └── models/            # Data models (1 file)
└── data/                  # Persistent storage

## Key Files to Check When Resuming

1. main.py - Entry point, understand app initialization
2. config.py - All constants and configuration
3. bot/handlers/__init__.py - How handlers are registered
4. bot/services/scheduler.py - Background tasks
5. bot/utils/state.py - State management

## Common Tasks and Solutions

### Add New Feature
1. Create handler in bot/handlers/
2. Create service in bot/services/ if complex logic
3. Register in bot/handlers/__init__.py
4. Update keyboards in bot/utils/keyboards.py

### Add New Source
Edit SOURCES list in config.py

### Modify AI Behavior
Edit prompts in bot/services/ai_generator.py

### Change Scheduling
Edit bot/services/scheduler.py

## Testing Commands

# Check structure
find . -name "*.py" -not -path "./venv/*" | wc -l  # Should be 24+

# Test imports
python -c "from bot.handlers import setup_handlers; print('OK')"

# Run bot
python main.py

## Key Patterns Used

- Singleton Services: parser_service, ai_generator, etc.
- Decorators: @admin_only, @error_handler
- Async State: All state operations are async
- Logging: Every module has logger = logging.getLogger(__name__)

## Environment Variables

Required in .env:
- TELEGRAM_TOKEN
- TELEGRAM_CHANNEL
- ADMIN_CHAT_ID
- OPENAI_API_KEY

## Git Commands

git add .
git commit -m "Your changes"
git push
