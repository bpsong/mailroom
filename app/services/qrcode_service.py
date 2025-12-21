"""QR code generation service for package tracking."""

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image
from io import BytesIO
import base64
from uuid import UUID

from app.services.system_settings_service import system_settings_service


class QRCodeService:
    """Service for generating QR codes for packages."""
    
    # Constants for 2cm x 2cm at 300 DPI
    CM_TO_INCH = 1 / 2.54
    TARGET_QR_CM = 2.0
    PRINT_DPI = 300
    TARGET_QR_PIXELS = int(TARGET_QR_CM * CM_TO_INCH * PRINT_DPI)  # 236 pixels
    
    async def get_base_url(self, fallback_url: str) -> str:
        """
        Get base URL for QR codes.
        
        Uses configured URL if available, otherwise falls back to request URL.
        
        Args:
            fallback_url: Fallback URL from request (e.g., request.base_url)
            
        Returns:
            Base URL to use for QR code generation
        """
        configured_url = await system_settings_service.get_qr_base_url()
        return configured_url if configured_url else fallback_url.rstrip('/')
    
    def create_tracking_url(self, package_id: UUID, base_url: str) -> str:
        """
        Create tracking URL for package.
        
        Args:
            package_id: Package UUID
            base_url: Base URL for the application
            
        Returns:
            Full URL to package detail page
        """
        return f"{base_url}/packages/{package_id}"
    
    def generate_qr_code(self, package_id: UUID, base_url: str) -> BytesIO:
        """
        Generate QR code PNG for package.
        
        Creates a QR code sized at 2cm x 2cm at 300 DPI for optimal print quality
        on sticker labels. Uses high error correction (ERROR_CORRECT_H) to ensure
        reliable scanning even if partially damaged or obscured.
        
        Args:
            package_id: Package UUID
            base_url: Base URL for the application
            
        Returns:
            BytesIO containing PNG image data with DPI metadata
        """
        tracking_url = self.create_tracking_url(package_id, base_url)
        
        # Configure QR code with high error correction
        qr = qrcode.QRCode(
            version=None,  # Auto-detect optimal version
            error_correction=ERROR_CORRECT_H,  # 30% error correction
            box_size=10,
            border=4,  # Minimum border per QR spec
        )
        
        qr.add_data(tracking_url)
        qr.make(fit=True)
        
        # Generate image and resize to exact dimensions
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        img = img.resize(
            (self.TARGET_QR_PIXELS, self.TARGET_QR_PIXELS),
            resample=Image.NEAREST
        )
        
        # Save with DPI metadata for print accuracy
        img_io = BytesIO()
        img.save(img_io, format='PNG', dpi=(self.PRINT_DPI, self.PRINT_DPI))
        img_io.seek(0)
        
        return img_io
    
    async def get_qr_code_base64(self, package_id: UUID, fallback_url: str) -> str:
        """
        Generate base64-encoded QR code for HTML embedding.
        
        This method is useful for embedding QR codes directly in HTML templates
        using data URIs.
        
        Args:
            package_id: Package UUID
            fallback_url: Fallback URL from request (e.g., request.base_url)
            
        Returns:
            Base64-encoded PNG image data (without data URI prefix)
        """
        base_url = await self.get_base_url(fallback_url)
        qr_code_io = self.generate_qr_code(package_id, base_url)
        return base64.b64encode(qr_code_io.getvalue()).decode('utf-8')


# Global instance
qrcode_service = QRCodeService()
