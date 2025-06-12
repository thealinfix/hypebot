# HypeBot - Sneaker & Fashion Release Monitor

Telegram bot for monitoring and publishing sneaker and fashion releases with AI-powered content generation.

## Features

- 🔍 **Multi-source monitoring**: SneakerNews, Hypebeast, Highsnobiety
- 🤖 **AI Integration**: GPT-4 for captions, DALL-E 3 for images, GPT-4 Vision for analysis
- ⏰ **Smart scheduling**: Post scheduling with timezone support
- 🏷 **Tag system**: Automatic brand/model/color extraction
- ⭐️ **Favorites**: Mark and auto-publish favorite posts
- 📊 **Analytics**: Detailed statistics and insights
- 🎨 **Image generation**: Custom covers for posts
- 💭 **Personal posts**: Create thought/opinion posts

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure
4. Run: `python main.py`

## Configuration

Edit `.env` file with your tokens:
- `TELEGRAM_TOKEN` - Bot token from @BotFather
- `TELEGRAM_CHANNEL` - Target channel
- `ADMIN_CHAT_ID` - Your Telegram ID
- `OPENAI_API_KEY` - OpenAI API key

## 🔧 For Developers

### Architecture Overview
- handlers/ - User interaction layer
- services/ - Business logic layer  
- utils/ - Shared utilities
- models/ - Data structures

### Adding New Features
See AI_ASSISTANT_CONTEXT.md for detailed guide

### Code Style
- Use type hints
- Async/await for I/O
- Comprehensive error handling
- Logging for debugging

### Roadmap
See DEVELOPMENT_ROADMAP.md for planned features
