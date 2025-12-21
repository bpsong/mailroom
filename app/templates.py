"""Shared Jinja2 templates configuration."""

from fastapi.templating import Jinja2Templates

from app.utils.template_helpers import csrf_token_value, csrf_input


# Create shared templates instance
templates = Jinja2Templates(directory="templates")

# Register global template functions
templates.env.globals["csrf_token_value"] = csrf_token_value
templates.env.globals["csrf_input"] = csrf_input
