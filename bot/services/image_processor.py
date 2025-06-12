"""
Image processing service
"""

from typing import Dict, Any, Optional, List, Tuple

import asyncio
import logging
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image
import aiofiles

from bot.utils.helpers import is_valid_image_url, sanitize_filename

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Service for image processing and manipulation"""
    
    def __init__(self):
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # Image size limits
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_dimension = 4096
        self.telegram_photo_size_limit = 5 * 1024 * 1024  # 5MB for photos
    
    async def download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL"""
        if not is_valid_image_url(url):
            logger.warning(f"Invalid image URL: {url}")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers, follow_redirects=True)
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"Non-image content type: {content_type}")
                    return None
                
                # Check file size
                content_length = int(response.headers.get('content-length', 0))
                if content_length > self.max_file_size:
                    logger.warning(f"Image too large: {content_length} bytes")
                    return None
                
                return response.content
                
        except httpx.TimeoutException:
            logger.error(f"Timeout downloading image: {url}")
        except httpx.RequestError as e:
            logger.error(f"Error downloading image: {e}")
        except Exception as e:
            logger.error(f"Unexpected error downloading image: {e}")
        
        return None
    
    async def validate_image(self, image_data: bytes) -> bool:
        """Validate image data"""
        try:
            # Check size
            if len(image_data) > self.max_file_size:
                logger.warning("Image data too large")
                return False
            
            # Try to open image
            with Image.open(BytesIO(image_data)) as img:
                # Check dimensions
                width, height = img.size
                if width > self.max_dimension or height > self.max_dimension:
                    logger.warning(f"Image dimensions too large: {width}x{height}")
                    return False
                
                # Check format
                if img.format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                    logger.warning(f"Unsupported image format: {img.format}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating image: {e}")
            return False
    
    async def optimize_for_telegram(self, image_data: bytes, 
                                  max_size: Optional[int] = None) -> bytes:
        """Optimize image for Telegram"""
        if max_size is None:
            max_size = self.telegram_photo_size_limit
        
        try:
            # Check if optimization needed
            if len(image_data) <= max_size:
                return image_data
            
            with Image.open(BytesIO(image_data)) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                    img = rgb_img
                
                # Start with original size
                quality = 95
                scale = 1.0
                
                while True:
                    # Scale if needed
                    if scale < 1.0:
                        new_size = (int(img.width * scale), int(img.height * scale))
                        temp_img = img.resize(new_size, Image.Resampling.LANCZOS)
                    else:
                        temp_img = img
                    
                    # Save to buffer
                    buffer = BytesIO()
                    temp_img.save(buffer, format='JPEG', quality=quality, optimize=True)
                    
                    # Check size
                    if buffer.tell() <= max_size or quality <= 20:
                        buffer.seek(0)
                        return buffer.read()
                    
                    # Reduce quality or scale
                    if quality > 70:
                        quality -= 10
                    else:
                        scale *= 0.9
                        quality = 85
                        
        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            return image_data  # Return original on error
    
    async def create_thumbnail(self, image_data: bytes, 
                             size: Tuple[int, int] = (320, 320)) -> bytes:
        """Create thumbnail from image"""
        try:
            with Image.open(BytesIO(image_data)) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Save to buffer
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=85, optimize=True)
                buffer.seek(0)
                
                return buffer.read()
                
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            raise
    
    async def download_multiple(self, urls: List[str], 
                              max_concurrent: int = 3) -> List[Optional[bytes]]:
        """Download multiple images concurrently"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(url: str) -> Optional[bytes]:
            async with semaphore:
                return await self.download_image(url)
        
        tasks = [download_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        images = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error downloading {urls[i]}: {result}")
                images.append(None)
            else:
                images.append(result)
        
        return images
    
    async def save_image(self, image_data: bytes, 
                        directory: Path, 
                        filename: Optional[str] = None) -> Optional[Path]:
        """Save image to disk"""
        try:
            # Create directory if needed
            directory.mkdir(parents=True, exist_ok=True)
            
            # Generate filename if not provided
            if not filename:
                import hashlib
                import time
                hash_str = hashlib.md5(image_data).hexdigest()[:8]
                filename = f"image_{int(time.time())}_{hash_str}.jpg"
            
            # Sanitize filename
            filename = sanitize_filename(filename)
            filepath = directory / filename
            
            # Save asynchronously
            async with aiofiles.open(filepath, 'wb') as f:
                await f.write(image_data)
            
            logger.info(f"Image saved to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            return None
    
    async def get_image_info(self, image_data: bytes) -> Dict[str, Any]:
        """Get image information"""
        try:
            with Image.open(BytesIO(image_data)) as img:
                return {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height,
                    'file_size': len(image_data),
                    'has_transparency': img.mode in ('RGBA', 'LA')
                }
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return {}
    
    async def create_collage(self, images: List[bytes], 
                           grid_size: Optional[Tuple[int, int]] = None,
                           spacing: int = 10,
                           background_color: Tuple[int, int, int] = (255, 255, 255)) -> bytes:
        """Create a collage from multiple images"""
        if not images:
            raise ValueError("No images provided")
        
        try:
            # Open all images
            pil_images = []
            for img_data in images:
                pil_images.append(Image.open(BytesIO(img_data)))
            
            # Determine grid size
            if not grid_size:
                count = len(pil_images)
                if count == 1:
                    grid_size = (1, 1)
                elif count == 2:
                    grid_size = (2, 1)
                elif count <= 4:
                    grid_size = (2, 2)
                elif count <= 6:
                    grid_size = (3, 2)
                elif count <= 9:
                    grid_size = (3, 3)
                else:
                    grid_size = (4, 3)
            
            cols, rows = grid_size
            
            # Calculate cell size (use smallest image dimensions)
            min_width = min(img.width for img in pil_images)
            min_height = min(img.height for img in pil_images)
            
            cell_width = min_width
            cell_height = min_height
            
            # Create canvas
            canvas_width = cols * cell_width + (cols - 1) * spacing
            canvas_height = rows * cell_height + (rows - 1) * spacing
            
            canvas = Image.new('RGB', (canvas_width, canvas_height), background_color)
            
            # Paste images
            for idx, img in enumerate(pil_images[:cols * rows]):
                row = idx // cols
                col = idx % cols
                
                # Resize image to fit cell
                img_resized = img.resize((cell_width, cell_height), Image.Resampling.LANCZOS)
                
                # Calculate position
                x = col * (cell_width + spacing)
                y = row * (cell_height + spacing)
                
                canvas.paste(img_resized, (x, y))
            
            # Save to buffer
            buffer = BytesIO()
            canvas.save(buffer, format='JPEG', quality=90, optimize=True)
            buffer.seek(0)
            
            # Clean up
            for img in pil_images:
                img.close()
            
            return buffer.read()
            
        except Exception as e:
            logger.error(f"Error creating collage: {e}")
            raise
    
    async def add_watermark(self, image_data: bytes, 
                          watermark_text: str,
                          position: str = 'bottom-right',
                          opacity: float = 0.5) -> bytes:
        """Add watermark to image"""
        try:
            from PIL import ImageDraw, ImageFont
            
            with Image.open(BytesIO(image_data)) as img:
                # Convert to RGBA for transparency
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Create watermark layer
                watermark = Image.new('RGBA', img.size, (255, 255, 255, 0))
                draw = ImageDraw.Draw(watermark)
                
                # Try to use a nice font, fallback to default
                try:
                    font_size = int(min(img.width, img.height) * 0.05)
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                except OSError:
                    font = ImageFont.load_default()
                
                # Get text size
                bbox = draw.textbbox((0, 0), watermark_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Calculate position
                margin = 20
                if position == 'bottom-right':
                    x = img.width - text_width - margin
                    y = img.height - text_height - margin
                elif position == 'bottom-left':
                    x = margin
                    y = img.height - text_height - margin
                elif position == 'top-right':
                    x = img.width - text_width - margin
                    y = margin
                elif position == 'top-left':
                    x = margin
                    y = margin
                else:  # center
                    x = (img.width - text_width) // 2
                    y = (img.height - text_height) // 2
                
                # Draw text
                draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, int(255 * opacity)))
                
                # Composite
                watermarked = Image.alpha_composite(img, watermark)
                
                # Convert back to RGB
                rgb_img = Image.new('RGB', watermarked.size, (255, 255, 255))
                rgb_img.paste(watermarked, mask=watermarked.split()[3])
                
                # Save to buffer
                buffer = BytesIO()
                rgb_img.save(buffer, format='JPEG', quality=90, optimize=True)
                buffer.seek(0)
                
                return buffer.read()
                
        except Exception as e:
            logger.error(f"Error adding watermark: {e}")
            return image_data  # Return original on error


# Singleton instance
image_processor = ImageProcessor()
