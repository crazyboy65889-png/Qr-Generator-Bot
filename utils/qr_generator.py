import qrcode
import io
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import asyncio
from typing import Optional
import logging

logger = logging.getLogger('QRGenerator')

class UltimateQRGenerator:
    """Ultimate QR code generator with advanced features"""
    
    def __init__(self):
        self.logo_cache = {}
        self.default_logo_size = 60
    
    async def generate_upi_qr(
        self,
        upi_id: str,
        name: str,
        amount: Optional[float] = None,
        note: Optional[str] = None,
        avatar_url: Optional[str] = None,
        color_scheme: Optional[dict] = None
    ) -> io.BytesIO:
        """
        Generate UPI QR code with logo and customization
        
        Args:
            upi_id: UPI ID
            name: Beneficiary name
            amount: Payment amount (optional)
            note: Payment note (optional)
            avatar_url: Avatar URL for logo (optional)
            color_scheme: Custom colors {front_color, back_color} (optional)
        """
        try:
            # Build UPI URL
            upi_url = self._build_upi_url(upi_id, name, amount, note)
            
            # QR Code generation
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=15,
                border=4,
            )
            qr.add_data(upi_url)
            qr.make(fit=True)
            
            # Color scheme
            front_color = color_scheme.get('front_color', '#000000') if color_scheme else '#000000'
            back_color = color_scheme.get('back_color', '#FFFFFF') if color_scheme else '#FFFFFF'
            
            img = qr.make_image(fill_color=front_color, back_color=back_color)
            img = img.convert("RGBA")
            
            # Add logo if available
            if avatar_url:
                try:
                    logo = await self._get_cached_avatar(avatar_url)
                    if logo:
                        img = self._add_center_logo(img, logo)
                except Exception as e:
                    logger.warning(f"Logo processing failed: {e}")
            
            # Add UPI ID overlay
            img = self._add_text_overlay(
                img,
                f"UPI: {upi_id}",
                position='bottom',
                opacity=128
            )
            
            # Convert to buffer
            buffer = io.BytesIO()
            img.save(buffer, format='PNG', quality=95, optimize=True)
            buffer.seek(0)
            
            logger.info(f"QR generated for {upi_id}")
            return buffer
            
        except Exception as e:
            logger.error(f"QR generation failed: {e}")
            raise Exception(f"Failed to generate QR: {str(e)}")
    
    def _build_upi_url(
        self,
        upi_id: str,
        name: str,
        amount: Optional[float],
        note: Optional[str]
    ) -> str:
        """Build UPI payment URL"""
        params = {
            'pa': upi_id,
            'pn': name.strip(),
            'cu': 'INR'
        }
        
        if amount and amount > 0:
            params['am'] = f"{amount:.2f}"
        
        if note:
            params['tn'] = note.strip()[:100]  # Limit note length
        
        # URL encode
        from urllib.parse import quote
        url_parts = [f"{k}={quote(str(v))}" for k, v in params.items()]
        return "upi://pay?" + "&".join(url_parts)
    
    async def _get_cached_avatar(self, url: str) -> Optional[Image.Image]:
        """Get avatar with caching"""
        if url in self.logo_cache:
            return self.logo_cache[url]
        
        try:
            logo = await self._download_image(url)
            if logo:
                # Resize
                logo = logo.resize((self.default_logo_size, self.default_logo_size), Image.Resampling.LANCZOS)
                # Cache for 1 hour
                self.logo_cache[url] = logo
                asyncio.create_task(self._clear_cache_after(url, 3600))
                return logo
        except Exception as e:
            logger.warning(f"Avatar download failed: {e}")
        
        return None
    
    async def _download_image(self, url: str) -> Optional[Image.Image]:
        """Download image from URL"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        return Image.open(io.BytesIO(data))
        except Exception as e:
            logger.error(f"Image download error: {e}")
        return None
    
    def _add_center_logo(self, qr_img: Image.Image, logo: Image.Image) -> Image.Image:
        """Add logo to center of QR code"""
        try:
            # Create circular mask for logo
            mask = Image.new('L', logo.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + logo.size, fill=255)
            
            # Apply mask
            logo.putalpha(mask)
            
            # Calculate position
            pos = (
                (qr_img.size[0] - logo.size[0]) // 2,
                (qr_img.size[1] - logo.size[1]) // 2
            )
            
            # Create white background for logo
            bg_size = (logo.size[0] + 10, logo.size[1] + 10)
            bg = Image.new('RGBA', bg_size, 'white')
            qr_img.paste(bg, (pos[0] - 5, pos[1] - 5))
            qr_img.paste(logo, pos, mask=logo)
            
            return qr_img
        except Exception as e:
            logger.error(f"Logo addition failed: {e}")
            return qr_img
    
    def _add_text_overlay(
        self,
        img: Image.Image,
        text: str,
        position: str = 'bottom',
        opacity: int = 255
    ) -> Image.Image:
        """Add text overlay to QR code"""
        try:
            draw = ImageDraw.Draw(img, 'RGBA')
            
            # Font size based on image size
            font_size = max(10, min(20, img.size[0] // 50))
            
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # Calculate text size
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Position
            if position == 'bottom':
                x = 10
                y = img.size[1] - text_height - 10
            
            # Add semi-transparent background
            bg_rect = [
                x - 5, y - 5,
                x + text_width + 5, y + text_height + 5
            ]
            draw.rectangle(bg_rect, fill=(255, 255, 255, opacity // 2))
            
            # Add text
            draw.text((x, y), text, font=font, fill=(0, 0, 0, opacity))
            
            return img
        except Exception as e:
            logger.warning(f"Text overlay failed: {e}")
            return img
    
    async def _clear_cache_after(self, url: str, seconds: int):
        """Clear cache after delay"""
        await asyncio.sleep(seconds)
        if url in self.logo_cache:
            del self.logo_cache[url]
  
