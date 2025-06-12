# Troubleshooting Guide

## Common Issues and Solutions

### Bot Won't Start
- Error: "No module named 'bot'" - Run from project root: cd ~/hypebot && python main.py
- Error: "TELEGRAM_TOKEN not set" - Copy .env.example to .env and add tokens
- Error: "version mismatch" - Run: pip install -r requirements.txt --upgrade

### Features Not Working
- Images not generating: Check OpenAI API key and credits
- Sources not parsing: Test with python -m bot.services.parser
- Scheduled posts not publishing: Check timezone and bot permissions

### Performance Issues
- High memory: Check state.json size, use /clean command
- Slow responses: Check API rate limits, enable connection pooling

### Data Issues
- Corrupted state.json: Backup and reset
- Duplicate posts: Clear sent_links, check deduplication logic

### Debug Mode
Create debug.py in root for testing all components
