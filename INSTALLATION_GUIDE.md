# HypeBot - Полное руководство по установке

## Требования
- Python 3.8+
- pip3
- Git
- Доступ к интернету

## Пошаговая установка

### 1. Клонирование репозитория
git clone https://github.com/yourusername/hypebot.git
cd hypebot

### 2. Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

### 3. Установка зависимостей
pip install -r requirements.txt

Если есть проблемы, установите пакеты по отдельности:
pip install python-telegram-bot==21.7
pip install openai==1.51.2
pip install httpx==0.27.2
pip install beautifulsoup4==4.12.3
pip install lxml==5.3.0
pip install pillow==11.0.0
pip install pytz==2024.2
pip install python-dotenv==1.0.1
pip install aiofiles==24.1.0

### 4. Настройка конфигурации
cp .env.example .env
nano .env  # или любой другой редактор

Заполните обязательные поля:
- TELEGRAM_TOKEN - получите от @BotFather
- TELEGRAM_CHANNEL - @username канала или ID чата
- ADMIN_CHAT_ID - ваш Telegram ID (получите от @userinfobot)
- OPENAI_API_KEY - ключ API от OpenAI

### 5. Настройка бота в Telegram
1. Создайте бота через @BotFather
2. Сохраните токен
3. Добавьте бота в канал как администратора
4. Дайте права на публикацию сообщений

### 6. Первый запуск
python main.py

### 7. Проверка работы
1. Напишите боту /start
2. Используйте /check для проверки источников
3. Используйте /preview для просмотра постов

## Решение проблем

### ModuleNotFoundError
pip install -r requirements.txt

### Permission denied
chmod +x run.sh

### Bot not responding
- Проверьте токен в .env
- Проверьте интернет соединение
- Проверьте логи: tail -f data/bot.log

## Обновление бота
git pull
pip install -r requirements.txt --upgrade

## Запуск в фоне (Linux)
nohup python main.py > output.log 2>&1 &

Или используйте systemd/supervisor для production.
