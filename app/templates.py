"""Shared Jinja2 templates configuration."""

from datetime import datetime

from fastapi.templating import Jinja2Templates

from app.utils.template_helpers import csrf_token_value, csrf_input


# Create shared templates instance
templates = Jinja2Templates(directory="templates")

# Register global template functions
templates.env.globals["csrf_token_value"] = csrf_token_value
templates.env.globals["csrf_input"] = csrf_input

# Footer globals
# current_year is a callable so it is evaluated at render time, not once at startup.
templates.env.globals["current_year"] = lambda: datetime.now().year


def _get_company_name() -> str:
    """Read company name from system_settings table, defaulting to 'Your Company'."""
    try:
        from app.database.connection import get_db
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                "SELECT value FROM system_settings WHERE key = 'company_name'",
            ).fetchone()
            return result[0] if result else "Your Company"
    except Exception:
        return "Your Company"


templates.env.globals["company_name"] = _get_company_name
