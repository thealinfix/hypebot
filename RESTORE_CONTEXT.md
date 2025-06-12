# HypeBot Refactoring Context

## Project Overview
- **Original**: Monolithic hypebot.py (2500+ lines)
- **Current**: Modular architecture with 20+ files
- **Tech**: Python 3.10+, python-telegram-bot, OpenAI API

## Architecture Decisions
1. **Separation of Concerns**: Each module has single responsibility
2. **Async First**: All I/O operations are async
3. **Dependency Injection**: Services are singletons
4. **State Management**: JSON-based with async file operations
5. **Error Handling**: Decorators for consistent error handling

## Module Descriptions
- **handlers/**: Handle user interactions
- **services/**: Business logic and external integrations
- **utils/**: Shared utilities and helpers
- **models/**: Data structures

## Next Steps
- Add database support
- Implement caching
- Add more tests
- Create web dashboard
