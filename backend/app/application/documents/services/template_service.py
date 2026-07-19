"""Jinja2 template rendering service for document generation."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape


class TemplateService:
    """Service for rendering Jinja2 HTML templates."""

    def __init__(self, template_dir: str = "backend/app/templates"):
        """Initialize template service with template directory."""
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml']),
        )

    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any],
    ) -> str:
        """Render a Jinja2 template with the given context.
        
        Args:
            template_name: Template file path relative to template directory
            context: Dictionary of variables to pass to the template
            
        Returns:
            Rendered HTML string
        """
        template = self.env.get_template(template_name)
        return template.render(**context)

    def get_template_path(self, document_type: str, template_name: str = "print.html") -> str:
        """Get the template path for a document type.
        
        Args:
            document_type: Type of document (work_order, purchase_order, etc.)
            template_name: Name of the template file (default: print.html)
            
        Returns:
            Template path relative to template directory
        """
        return f"{document_type}/{template_name}"
