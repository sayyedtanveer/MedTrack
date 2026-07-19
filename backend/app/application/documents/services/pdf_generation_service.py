"""PDF generation service using WeasyPrint."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import WeasyPrint with graceful fallback
WEASYPRINT_AVAILABLE = False
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
    logger.info("WeasyPrint imported successfully - PDF generation enabled")
except ImportError as e:
    logger.warning(f"WeasyPrint not available: {e} - PDF generation disabled")
except OSError as e:
    logger.warning(f"WeasyPrint dependencies missing: {e} - PDF generation disabled")


class PDFGenerationService:
    """Service for generating PDFs from HTML using WeasyPrint."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize PDF generation service.
        
        Args:
            base_url: Base URL for resolving relative paths in HTML
        """
        self.base_url = base_url
        self.available = WEASYPRINT_AVAILABLE

    def generate_pdf_from_html(
        self,
        html_content: str,
        css_content: Optional[str] = None,
    ) -> bytes:
        """Generate PDF from HTML content.
        
        Args:
            html_content: HTML string to convert to PDF
            css_content: Optional CSS string for styling
            
        Returns:
            PDF as bytes
            
        Raises:
            RuntimeError: If WeasyPrint is not available
        """
        if not self.available:
            raise RuntimeError(
                "PDF generation is not available. WeasyPrint dependencies are missing."
            )
        
        # Create HTML object
        html_obj = HTML(string=html_content, base_url=self.base_url)
        
        # Create CSS object if provided
        stylesheets = []
        if css_content:
            stylesheets.append(CSS(string=css_content))
        
        # Generate PDF
        pdf_bytes = html_obj.write_pdf(stylesheets=stylesheets)
        
        return pdf_bytes

    def generate_pdf_from_file(
        self,
        html_file_path: str,
        css_file_path: Optional[str] = None,
    ) -> bytes:
        """Generate PDF from HTML file.
        
        Args:
            html_file_path: Path to HTML file
            css_file_path: Optional path to CSS file
            
        Returns:
            PDF as bytes
            
        Raises:
            RuntimeError: If WeasyPrint is not available
        """
        if not self.available:
            raise RuntimeError(
                "PDF generation is not available. WeasyPrint dependencies are missing."
            )
        
        # Create HTML object from file
        html_obj = HTML(filename=html_file_path, base_url=self.base_url)
        
        # Create CSS object if provided
        stylesheets = []
        if css_file_path:
            stylesheets.append(CSS(filename=css_file_path))
        
        # Generate PDF
        pdf_bytes = html_obj.write_pdf(stylesheets=stylesheets)
        
        return pdf_bytes
