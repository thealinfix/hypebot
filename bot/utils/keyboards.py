"""
Telegram keyboard builders
"""
from typing import List, Optional, Dict, Any, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
import logging

logger = logging.getLogger(__name__)


class KeyboardBuilder:
    """Builder for creating Telegram keyboards"""
    
    @staticmethod
    def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
        """Build main menu keyboard"""
        keyboard_buttons = [
            [InlineKeyboardButton("📊 Статус бота", callback_data="cmd_status")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="cmd_help")]
        ]
        
        if is_admin:
            keyboard_buttons.extend([
                [
                    InlineKeyboardButton("👁 Превью постов", callback_data="cmd_preview"),
                    InlineKeyboardButton("🔄 Проверить релизы", callback_data="cmd_check")
                ],
                [
                    InlineKeyboardButton("💭 Создать мысли", callback_data="cmd_thoughts"),
                    InlineKeyboardButton("⏰ Запланированные", callback_data="cmd_scheduled")
                ],
                [
                    InlineKeyboardButton("📈 Статистика", callback_data="cmd_stats"),
                    InlineKeyboardButton("🤖 Авто-публикация", callback_data="cmd_auto_menu")
                ],
                [
                    InlineKeyboardButton("⚙️ Настройки", callback_data="cmd_settings"),
                    InlineKeyboardButton("🧹 Очистка", callback_data="cmd_clean_menu")
                ],
                [
                    InlineKeyboardButton("🔧 Инструменты", callback_data="cmd_tools_menu")
                ]
            ])
        
        return InlineKeyboardMarkup(keyboard_buttons)
    
    @staticmethod
    def back_to_main() -> InlineKeyboardMarkup:
        """Simple back to main menu button"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
        ])
    
    @staticmethod
    def preview_navigation(current_idx: int, total: int, post_id: str, 
                          is_favorite: bool = False) -> InlineKeyboardMarkup:
        """Build preview navigation keyboard"""
        keyboard_buttons = []
        
        # Navigation buttons
        nav_buttons = []
        if current_idx > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"preview_prev:{current_idx}"))
        nav_buttons.append(InlineKeyboardButton(f"{current_idx + 1}/{total}", callback_data="noop"))
        if current_idx < total - 1:
            nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"preview_next:{current_idx}"))
        
        keyboard_buttons.append(nav_buttons)
        
        # Action buttons
        keyboard_buttons.append([
            InlineKeyboardButton("👁 Полный просмотр", callback_data=f"preview_full:{post_id}"),
            InlineKeyboardButton("⭐️" if is_favorite else "☆", callback_data=f"toggle_fav:{post_id}")
        ])
        
        keyboard_buttons.append([
            InlineKeyboardButton("🎨 Генерировать обложку", callback_data=f"gen_cover:{post_id}"),
            InlineKeyboardButton("⏰ Запланировать", callback_data=f"schedule:{post_id}")
        ])
        
        keyboard_buttons.append([
            InlineKeyboardButton("🏷 Фильтр по тегам", callback_data="filter_tags"),
            InlineKeyboardButton("❌ Закрыть", callback_data="preview_close")
        ])
        
        keyboard_buttons.append([
            InlineKeyboardButton("🏠 Главное меню", callback_data="cmd_back_main")
        ])
        
        return InlineKeyboardMarkup(keyboard_buttons)
    
    @staticmethod
    def moderation(post_id: str) -> InlineKeyboardMarkup:
        """Build moderation keyboard"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Опубликовать", callback_data=f"approve:{post_id}")],
            [InlineKeyboardButton("🔄 Перегенерировать текст", callback_data=f"regen:{post_id}")],
            [
                InlineKeyboardButton("🎨 Генерировать обложку", callback_data=f"gen_cover_full:{post_id}"),
                InlineKeyboardButton("✏️ Свой промпт", callback_data=f"custom_prompt:{post_id}")
            ],
            [
                InlineKeyboardButton("↩️ Вернуть оригинал", callback_data=f"revert_img:{post_id}"),
                InlineKeyboardButton("❌ Пропустить", callback_data=f"reject:{post_id}")
            ],
            [
                InlineKeyboardButton("◀️ Вернуться к превью", callback_data=f"back_preview:{post_id}"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="cmd_back_main")
            ]
        ])
    
    @staticmethod
    def thoughts_actions(has_image: bool = False) -> InlineKeyboardMarkup:
        """Build thoughts action keyboard"""
        buttons = [
            [InlineKeyboardButton("📤 Опубликовать", callback_data="publish_thought")],
            [InlineKeyboardButton("🔄 Перегенерировать", callback_data="regen_thought")],
            [InlineKeyboardButton("🎨 Генерировать обложку", callback_data="gen_thought_cover")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_thought")]
        ]
        
        if has_image:
            buttons.insert(2, [InlineKeyboardButton("🖼 Удалить изображение", callback_data="remove_thought_image")])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def settings_menu() -> InlineKeyboardMarkup:
        """Build settings menu keyboard"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Изменить канал", callback_data="settings_channel")],
            [InlineKeyboardButton("🕐 Изменить временную зону", callback_data="settings_timezone")],
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
        ])
    
    @staticmethod
    def timezone_selection() -> InlineKeyboardMarkup:
        """Build timezone selection keyboard"""
        from bot.utils.time_utils import get_timezone_list
        
        keyboard_buttons = []
        for name, tz in get_timezone_list():
            callback_data = f"tz_{tz.replace('/', '_')}"
            keyboard_buttons.append([InlineKeyboardButton(name, callback_data=callback_data)])
        
        keyboard_buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="cmd_settings")])
        
        return InlineKeyboardMarkup(keyboard_buttons)
    
    @staticmethod
    def clean_menu() -> InlineKeyboardMarkup:
        """Build clean menu keyboard"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 Старые посты", callback_data="clean_old")],
            [InlineKeyboardButton("📝 Очередь постов", callback_data="clean_pending")],
            [InlineKeyboardButton("✅ Обработанные", callback_data="clean_sent")],
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
        ])
    
    @staticmethod
    def tools_menu() -> InlineKeyboardMarkup:
        """Build tools menu keyboard"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Тест источников", callback_data="tool_test_sources")],
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
        ])
    
    @staticmethod
    def auto_publish_menu(is_enabled: bool, interval_minutes: int) -> InlineKeyboardMarkup:
        """Build auto-publish menu keyboard"""
        toggle_text = "🔴 Выключить" if is_enabled else "🟢 Включить"
        
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(toggle_text, callback_data="auto_toggle")],
            [
                InlineKeyboardButton("30 мин", callback_data="auto_interval:1800"),
                InlineKeyboardButton("1 час", callback_data="auto_interval:3600"),
                InlineKeyboardButton("2 часа", callback_data="auto_interval:7200")
            ],
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")]
        ])
    
    @staticmethod
    def scheduled_posts(posts: List[Tuple[str, Dict[str, Any]]]) -> InlineKeyboardMarkup:
        """Build scheduled posts keyboard"""
        keyboard_buttons = []
        
        for post_id, _ in posts:
            keyboard_buttons.append([
                InlineKeyboardButton("✏️ Изменить", callback_data=f"edit_schedule:{post_id}"),
                InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_schedule:{post_id}")
            ])
        
        keyboard_buttons.append([InlineKeyboardButton("◀️ Назад в меню", callback_data="cmd_back_main")])
        
        return InlineKeyboardMarkup(keyboard_buttons)
    
    @staticmethod
    def filter_tags(tags: Dict[str, List[str]]) -> InlineKeyboardMarkup:
        """Build tag filter keyboard"""
        keyboard_buttons = []
        
        # Brand buttons
        if tags.get("brands"):
            brand_buttons = []
            for brand in sorted(tags["brands"])[:3]:
                brand_buttons.append(
                    InlineKeyboardButton(
                        brand.title(), 
                        callback_data=f"filter_brand:{brand}"
                    )
                )
            if brand_buttons:
                keyboard_buttons.append(brand_buttons)
        
        # Model buttons
        if tags.get("models"):
            model_buttons = []
            for model in sorted(tags["models"])[:3]:
                model_buttons.append(
                    InlineKeyboardButton(
                        model.upper(), 
                        callback_data=f"filter_model:{model}"
                    )
                )
            if model_buttons:
                keyboard_buttons.append(model_buttons)
        
        # Type buttons
        if tags.get("types"):
            type_buttons = []
            for rtype in sorted(tags["types"])[:3]:
                type_buttons.append(
                    InlineKeyboardButton(
                        rtype.title(), 
                        callback_data=f"filter_type:{rtype}"
                    )
                )
            if type_buttons:
                keyboard_buttons.append(type_buttons)
        
        keyboard_buttons.extend([
            [InlineKeyboardButton("🔄 Сбросить фильтры", callback_data="filter_reset")],
            [InlineKeyboardButton("◀️ Назад", callback_data="preview_close")]
        ])
        
        return InlineKeyboardMarkup(keyboard_buttons)
    
    @staticmethod
    def yes_no(callback_prefix: str) -> InlineKeyboardMarkup:
        """Simple yes/no keyboard"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да", callback_data=f"{callback_prefix}_yes"),
                InlineKeyboardButton("❌ Нет", callback_data=f"{callback_prefix}_no")
            ]
        ])
    
    @staticmethod
    def cancel() -> InlineKeyboardMarkup:
        """Simple cancel button"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ])
    
    @staticmethod
    def pagination(items: List[Any], page: int, per_page: int = 10, 
                  callback_prefix: str = "page") -> Tuple[List[Any], Optional[InlineKeyboardMarkup]]:
        """Build paginated keyboard"""
        total_pages = (len(items) + per_page - 1) // per_page
        
        if total_pages <= 1:
            return items, None
        
        start_idx = page * per_page
        end_idx = min(start_idx + per_page, len(items))
        page_items = items[start_idx:end_idx]
        
        buttons = []
        
        # Page navigation
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"{callback_prefix}:{page-1}"))
        
        nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
        
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"{callback_prefix}:{page+1}"))
        
        buttons.append(nav_buttons)
        
        return page_items, InlineKeyboardMarkup(buttons)


def remove_keyboard() -> ReplyKeyboardMarkup:
    """Remove reply keyboard"""
    return ReplyKeyboardMarkup([[]], resize_keyboard=True, one_time_keyboard=True)
