# HypeBot - Quick Start Guide

## 1. Configuration
Edit .env file with your credentials:

TELEGRAM_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHANNEL=@your_channel_or_chat_id
ADMIN_CHAT_ID=your_telegram_user_id
OPENAI_API_KEY=sk-your_openai_api_key

## 2. Run the bot

# With virtual environment (recommended)
source venv/bin/activate
python main.py

# Or directly
python3 main.py

# Or using the run script
./run.sh

## 3. Bot Commands
- /start - Main menu
- /preview - Browse pending posts
- /check - Check for new releases
- /thoughts <topic> - Create personal post
- /stats - View statistics
- /help - Get help

## 4. First Steps
1. Start the bot with /start
2. Run /check to fetch initial posts
3. Use /preview to browse and moderate
4. Posts are published to your configured channel

## 5. Troubleshooting
- Check logs in data/bot.log
- Verify all tokens in .env
- Ensure bot is admin in channel
- Check internet connection for API access
