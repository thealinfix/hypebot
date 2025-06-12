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

## Common Improvements and How to Implement Them

### Adding New Parsing Source
1. Add source configuration to SOURCES in config.py
2. If custom parsing needed, add method to bot/services/parser.py
3. Test with: python -m bot.services.parser test_sources

### Adding New AI Feature
1. Create new method in bot/services/ai_generator.py
2. Add handler in appropriate file in bot/handlers/
3. Register handler in bot/handlers/__init__.py
4. Update keyboards in bot/utils/keyboards.py if needed

### Database Integration
1. Create schema in bot/models/database.py
2. Add database service in bot/services/db.py
3. Update bot/utils/state.py to use DB
4. Create migration script in scripts/migrate_to_db.py

### Performance Optimization Tips
- Current bottlenecks: Synchronous image downloads, Sequential source parsing
- Solutions: Use asyncio.gather() for parallel operations

### Adding New Command
1. Create command handler in bot/handlers/commands.py
2. Register in bot/handlers/__init__.py
3. Add to help text in bot/handlers/commands.py

### Error Handling Pattern
- Use try/except blocks
- Log errors with logger.error()
- Notify admin for critical errors
- Re-raise unexpected errors

### Debugging Tips
1. Enable debug logging: logging.basicConfig(level=logging.DEBUG)
2. Test specific module: python -m bot.services.parser
3. Check state: cat data/state.json | python -m json.tool

### Performance Profiling
Use cProfile and pstats for profiling bot performance
