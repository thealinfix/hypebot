#!/bin/bash
# HypeBot runner script

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Copy .env.example to .env and edit with your tokens"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    exit 1
fi

# Run the bot
echo "🚀 Starting HypeBot..."
python3 main.py
