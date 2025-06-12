"""
AI content generation service using OpenAI
"""
import base64
import logging
from typing import Optional, List, Dict, Any
from io import BytesIO

from openai import AsyncOpenAI
from PIL import Image

from config import OPENAI_API_KEY, IMAGE_STYLES
from bot.utils.helpers import is_valid_url

logger = logging.getLogger(__name__)


class AIGenerator:
    """Service for AI content generation"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        # Model fallback chain
        self.text_models = ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
        self.vision_model = "gpt-4-vision-preview"
        self.image_model = "dall-e-3"
    
    async def generate_caption(self, title: str, context: str = "", 
                             category: str = "sneakers", 
                             is_thought: bool = False,
                             image_description: str = "") -> str:
        """Generate caption for post"""
        try:
            if is_thought:
                return await self._generate_thought_caption(title, image_description)
            else:
                return await self._generate_post_caption(title, context, category)
        except Exception as e:
            logger.error(f"Error generating caption: {e}")
            return self._get_fallback_caption(title, is_thought)
    
    async def _generate_post_caption(self, title: str, context: str, category: str) -> str:
        """Generate regular post caption"""
        system_prompt = """Ты — автор Telegram-канала про кроссовки и уличную моду. Твоя задача — писать короткие, цепляющие и стильные посты о релизах, трендах и коллаборациях. 

ПРАВИЛА ИСПОЛЬЗОВАНИЯ ЭМОДЗИ:
- ТОЛЬКО один эмодзи в начале поста (настроение/тема)
- Можно добавить ОДИН эмодзи в конце (призыв/вопрос)
- НЕ используй эмодзи внутри текста
- НЕ используй эмодзи в каждом абзаце
- Подходящие эмодзи для начала: 🔥 ⚡️ 💫 👟 🚨
- Подходящие для конца: 👀 🤔 💭

Пиши в нейтрально-молодёжном тоне: без пафоса, без канцелярита, без жаргона. Стиль — живой, лёгкий, современный.

Структура поста:
1. Начни с ОДНОГО эмодзи и цепляющей фразы (1-2 предложения)
2. Суть релиза: бренд, модель, особенности - БЕЗ эмодзи
3. Детали: материалы, цвета, что выделяет - БЕЗ эмодзи
4. Завершение: мнение или вопрос (можно добавить ОДИН эмодзи в конце)

Избегай: длинных текстов, технических деталей, рекламных клише.
Максимум 600 символов."""
        
        user_prompt = f"Заголовок: {title}\nДетали: {context[:500] if context else 'Нет информации'}"
        
        for model in self.text_models:
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    temperature=0.8,
                    max_tokens=300,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                )
                
                generated = response.choices[0].message.content.strip()
                logger.info(f"Caption generated successfully with {model}")
                
                # Add title if not present
                if title.lower() not in generated.lower():
                    generated = f"<b>{title}</b>\n\n{generated}"
                
                return generated
                
            except Exception as e:
                logger.error(f"Error with model {model}: {e}")
                continue
        
        # Fallback
        return self._get_fallback_caption(title, False)
    
    async def _generate_thought_caption(self, topic: str, image_description: str = "") -> str:
        """Generate thought/personal post caption"""
        system_prompt = """Ты ведешь личный блог о кроссовках и уличной моде. Пиши от первого лица, как будто делишься своими мыслями с друзьями. Стиль непринужденный, с эмоциями и личным отношением. 

ПРАВИЛА ИСПОЛЬЗОВАНИЯ ЭМОДЗИ:
- ТОЛЬКО в начале абзаца или всего поста
- НЕ БОЛЕЕ одного эмодзи на абзац
- НЕ используй эмодзи внутри предложений
- Подходящие эмодзи: 😍 🔥 💭 🤔 😎 ✨ 👟

Можешь использовать:
- Личные впечатления ("мне кажется", "по-моему", "честно говоря")
- Эмоции ("обалдел когда увидел", "влюбился с первого взгляда")
- Сравнения из жизни
- Немного юмора или иронии где уместно

Максимум 500 символов. Не используй заезженные фразы."""
        
        if image_description:
            user_prompt = f"Напиши пост-размышление на основе изображения и темы.\nТема: {topic}\nОписание изображения: {image_description}"
        else:
            user_prompt = f"Напиши пост-размышление о: {topic}"
        
        for model in self.text_models:
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    temperature=0.9,
                    max_tokens=300,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                )
                
                generated = response.choices[0].message.content.strip()
                logger.info(f"Thought caption generated successfully with {model}")
                return generated
                
            except Exception as e:
                logger.error(f"Error with model {model}: {e}")
                continue
        
        # Fallback
        return self._get_fallback_caption(topic, True)
    
    def _get_fallback_caption(self, title: str, is_thought: bool) -> str:
        """Get fallback caption when AI fails"""
        if is_thought:
            return f"💭 {title}\n\nЧто думаете?"
        else:
            return f"<b>{title}</b>\n\n🔥 Новый релиз. Подробности скоро!"
    
    async def generate_image(self, prompt: str, style: str = "photographic") -> Optional[str]:
        """Generate image using DALL-E 3"""
        try:
            logger.info(f"Generating image with prompt: {prompt[:50]}...")
            
            # Enhance prompt based on style
            enhanced_prompt = self._enhance_image_prompt(prompt, style)
            
            response = await self.client.images.generate(
                model=self.image_model,
                prompt=enhanced_prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            logger.info("Image generated successfully")
            return image_url
            
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return None
    
    def _enhance_image_prompt(self, prompt: str, style: str) -> str:
        """Enhance image prompt based on style"""
        style_enhancements = {
            "photographic": "professional photography, studio lighting, high quality, sharp focus, 4k resolution",
            "editorial": "fashion magazine style, editorial photography, trendy aesthetic, professional",
            "artistic": "digital art, creative composition, vibrant colors, artistic interpretation",
            "creative": "imaginative, unique perspective, creative design, eye-catching",
        }
        
        enhancement = style_enhancements.get(style, "high quality, professional")
        return f"{prompt}, {enhancement}"
    
    async def analyze_image(self, image_data: bytes) -> str:
        """Analyze image using GPT-4 Vision"""
        try:
            # Convert to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            response = await self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Опиши что изображено на этой картинке. Особое внимание удели деталям, цветам, стилю. Если это кроссовки или одежда - опиши модель, бренд, особенности дизайна."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            description = response.choices[0].message.content.strip()
            logger.info("Image analyzed successfully")
            return description
            
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return ""
    
    async def generate_custom_image(self, post_title: str, style_key: str = "sneakers", 
                                  custom_prompt: Optional[str] = None) -> Optional[str]:
        """Generate custom image for post"""
        try:
            # Get style configuration
            style_config = IMAGE_STYLES.get(style_key, IMAGE_STYLES["sneakers"])
            
            # Build prompt
            if custom_prompt:
                prompt = style_config["prompt_template"].format(custom_prompt=custom_prompt)
            else:
                prompt = style_config["prompt_template"].format(title=post_title)
            
            # Generate image
            return await self.generate_image(prompt, style_config["style"])
            
        except Exception as e:
            logger.error(f"Error generating custom image: {e}")
            return None
    
    async def improve_text(self, text: str, instruction: str) -> str:
        """Improve or modify text based on instruction"""
        try:
            for model in self.text_models:
                try:
                    response = await self.client.chat.completions.create(
                        model=model,
                        temperature=0.7,
                        messages=[
                            {
                                "role": "system",
                                "content": "Ты профессиональный редактор текстов для социальных сетей."
                            },
                            {
                                "role": "user",
                                "content": f"Улучши этот текст согласно инструкции.\n\nТекст: {text}\n\nИнструкция: {instruction}"
                            }
                        ],
                    )
                    
                    return response.choices[0].message.content.strip()
                    
                except Exception as e:
                    logger.error(f"Error with model {model}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error improving text: {e}")
        
        return text  # Return original if failed
    
    async def generate_hashtags(self, text: str, category: str = "sneakers") -> str:
        """Generate relevant hashtags for text"""
        try:
            prompt = f"Сгенерируй 5-7 релевантных хэштегов для этого поста о {'кроссовках' if category == 'sneakers' else 'моде'}. Текст: {text[:200]}"
            
            for model in self.text_models:
                try:
                    response = await self.client.chat.completions.create(
                        model=model,
                        temperature=0.5,
                        max_tokens=100,
                        messages=[
                            {
                                "role": "system",
                                "content": "Генерируй только хэштеги, разделенные пробелами. Используй как английские, так и русские хэштеги."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                    )
                    
                    hashtags = response.choices[0].message.content.strip()
                    # Ensure hashtags start with #
                    hashtags = ' '.join(f"#{tag.lstrip('#')}" for tag in hashtags.split())
                    return hashtags
                    
                except Exception as e:
                    logger.error(f"Error with model {model}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error generating hashtags: {e}")
        
        # Fallback
        if category == "sneakers":
            return "#sneakers #кроссовки #streetwear #обувь"
        else:
            return "#fashion #мода #streetwear #style"
    
    async def check_content_appropriateness(self, text: str) -> bool:
        """Check if content is appropriate for posting"""
        try:
            response = await self.client.moderations.create(input=text)
            
            results = response.results[0]
            
            # Check if any category is flagged
            flagged = results.flagged
            
            if flagged:
                logger.warning(f"Content flagged by moderation: {results.categories}")
            
            return not flagged
            
        except Exception as e:
            logger.error(f"Error checking content appropriateness: {e}")
            return True  # Allow by default if check fails


# Singleton instance
ai_generator = AIGenerator()
