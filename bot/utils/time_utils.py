"""
Time and timezone utilities
"""
import re
import pytz
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def get_user_timezone(state: dict) -> pytz.timezone:
    """Get user timezone from state"""
    from config import DEFAULT_TIMEZONE
    return pytz.timezone(state.get("timezone", DEFAULT_TIMEZONE))


def localize_datetime(dt: datetime, tz: pytz.timezone = None) -> datetime:
    """Convert UTC time to local"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    if tz is None:
        from config import DEFAULT_TIMEZONE
        tz = pytz.timezone(DEFAULT_TIMEZONE)
    
    return dt.astimezone(tz)


def format_local_time(dt: datetime, tz: pytz.timezone = None) -> str:
    """Format time in local timezone"""
    local_dt = localize_datetime(dt, tz)
    return local_dt.strftime("%d.%m.%Y %H:%M")


def format_date_for_display(date_input: str | datetime) -> str:
    """Format date for display"""
    try:
        if isinstance(date_input, str):
            date = datetime.fromisoformat(date_input.replace('Z', '+00:00'))
        else:
            date = date_input
        
        # Convert to local time
        local_date = localize_datetime(date)
        now = localize_datetime(datetime.now(timezone.utc))
        diff = now - local_date
        
        if diff.days == 0:
            return "Сегодня"
        elif diff.days == 1:
            return "Вчера"
        elif diff.days < 7:
            return f"{diff.days} дней назад"
        else:
            return local_date.strftime("%d.%m.%Y")
    except Exception as e:
        logger.error(f"Error formatting date: {e}")
        return "Недавно"


def parse_schedule_time(text: str, user_tz: pytz.timezone) -> Optional[datetime]:
    """Parse time/date from text with timezone support"""
    try:
        text = text.strip()
        now = datetime.now(user_tz)
        
        # 1. Time only HH:MM
        time_match = re.match(r'^(\d{1,2}):(\d{2})$', text)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                scheduled = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                if scheduled <= now:
                    scheduled += timedelta(days=1)
                return scheduled.astimezone(timezone.utc)
        
        # 2. Date and time DD.MM HH:MM
        datetime_match = re.match(r'^(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})$', text)
        if datetime_match:
            day = int(datetime_match.group(1))
            month = int(datetime_match.group(2))
            hours = int(datetime_match.group(3))
            minutes = int(datetime_match.group(4))
            year = now.year
            
            if 1 <= day <= 31 and 1 <= month <= 12 and 0 <= hours <= 23 and 0 <= minutes <= 59:
                scheduled = user_tz.localize(datetime(year, month, day, hours, minutes))
                if scheduled < now:
                    scheduled = scheduled.replace(year=year + 1)
                return scheduled.astimezone(timezone.utc)
        
        # 3. Relative time +1h, +30m, +2d
        relative_match = re.match(r'^\+(\d+)([hmd])$', text.lower())
        if relative_match:
            amount = int(relative_match.group(1))
            unit = relative_match.group(2)
            
            utc_now = datetime.now(timezone.utc)
            if unit == 'h' and 1 <= amount <= 24:
                return utc_now + timedelta(hours=amount)
            elif unit == 'm' and 1 <= amount <= 1440:
                return utc_now + timedelta(minutes=amount)
            elif unit == 'd' and 1 <= amount <= 30:
                return utc_now + timedelta(days=amount)
        
    except Exception as e:
        logger.error(f"Error parsing time: {e}")
    
    return None


def parse_date_from_rss(item) -> datetime:
    """Parse date from RSS element"""
    try:
        date_elem = item.find("pubDate") or item.find("published") or item.find("dc:date")
        if date_elem:
            date_str = date_elem.get_text(strip=True)
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
    except Exception as e:
        logger.error(f"Error parsing RSS date: {e}")
    
    return datetime.now(timezone.utc)


def get_timezone_list():
    """Get list of available timezones"""
    return [
        ("🇷🇺 Москва", "Europe/Moscow"),
        ("🇷🇺 Санкт-Петербург", "Europe/Moscow"),
        ("🇷🇺 Екатеринбург", "Asia/Yekaterinburg"),
        ("🇷🇺 Новосибирск", "Asia/Novosibirsk"),
        ("🇷🇺 Владивосток", "Asia/Vladivostok"),
        ("🇺🇦 Киев", "Europe/Kiev"),
        ("🇰🇿 Алматы", "Asia/Almaty"),
        ("🇧🇾 Минск", "Europe/Minsk"),
        ("🇺🇸 Нью-Йорк", "America/New_York"),
        ("🇬🇧 Лондон", "Europe/London"),
    ]
