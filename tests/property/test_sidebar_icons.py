"""Property-based tests for sidebar SVG icon consistency.

Feature: ui-improvements
Property 1: Sidebar uses only SVG icons at consistent size
Validates: Requirements 2.1, 2.2, 2.3
"""

import re
import unicodedata
from pathlib import Path
from types import SimpleNamespace
import pytest
from bs4 import BeautifulSoup
from hypothesis import given, settings
from hypothesis import strategies as st
from jinja2 import Environment, FileSystemLoader

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

# Unicode emoji ranges — broad coverage of common emoji blocks
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F9FF"   # Misc symbols, emoticons, transport, etc.
    "\U00002600-\U000027BF"   # Misc symbols, dingbats
    "\U0000FE00-\U0000FE0F"   # Variation selectors
    "\U00002702-\U000027B0"   # Dingbats
    "\U000024C2-\U0001F251"   # Enclosed chars, CJK compat
    "]+",
    flags=re.UNICODE,
)


def _has_emoji(text: str) -> bool:
    """Return True if *text* contains any Unicode emoji character."""
    if _EMOJI_PATTERN.search(text):
        return True
    # Also catch characters whose Unicode category starts with 'S' (Symbol)
    # that are commonly used as emoji (e.g., ☎, ✉, ★).
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("S") and ord(ch) > 127:
            return True
    return False


def _make_jinja_env() -> Environment:
    """Return a Jinja2 Environment pointed at the real templates directory."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    # Inject the globals that base.html expects
    env.globals["current_year"] = lambda: 2026
    env.globals["company_name"] = "Test Company"
    env.globals["csrf_token_value"] = lambda request=None: "test-csrf-token"
    env.globals["csrf_input"] = lambda request=None: ""
    # Stub FastAPI's url_for so the <head> CSS link renders without error
    env.globals["url_for"] = lambda name, **kwargs: f"/static/{kwargs.get('path', '')}"
    return env


def _make_request(path: str = "/dashboard") -> SimpleNamespace:
    """Return a minimal mock request object that satisfies base.html's usage."""
    url = SimpleNamespace(path=path)
    return SimpleNamespace(url=url, cookies={}, session={})


def _make_user(role: str) -> SimpleNamespace:
    """Return a minimal user object for the given role."""
    return SimpleNamespace(
        id=1,
        username="testuser",
        full_name="Test User",
        role=role,
        is_active=True,
    )


def _render_sidebar_html(role: str) -> str:
    """Render base.html with the given user role and return the full HTML."""
    env = _make_jinja_env()
    template = env.get_template("base.html")
    html = template.render(
        request=_make_request(),
        user=_make_user(role),
        title="Test Page",
    )
    return html


def _get_sidebar_nav_links(html: str):
    """Parse HTML and return all <a> elements inside the sidebar <aside>."""
    soup = BeautifulSoup(html, "html.parser")
    aside = soup.find("aside", attrs={"aria-label": "Sidebar navigation"})
    assert aside is not None, "Sidebar <aside> element not found in rendered HTML"
    return aside.find_all("a", href=True)


# ---------------------------------------------------------------------------
# Property 1: Sidebar uses only SVG icons at consistent size
# Validates: Requirements 2.1, 2.2, 2.3
# ---------------------------------------------------------------------------

@given(role=st.sampled_from(["operator", "admin", "super_admin"]))
@settings(max_examples=100, deadline=None)
def test_property_1_sidebar_uses_only_svg_icons_at_consistent_size(role: str):
    """**Validates: Requirements 2.1, 2.2, 2.3**

    For any authenticated user role, every navigation link item in the sidebar
    SHALL contain an SVG element with classes 'w-5' and 'h-5', and SHALL NOT
    contain any Unicode emoji code points in its text content.
    """
    html = _render_sidebar_html(role)
    nav_links = _get_sidebar_nav_links(html)

    assert len(nav_links) > 0, f"No sidebar nav links found for role '{role}'"

    for link in nav_links:
        href = link.get("href", "")

        # Requirement 2.1 — every nav link must contain an SVG icon
        svg = link.find("svg")
        assert svg is not None, (
            f"Nav link href='{href}' (role={role}) has no SVG icon"
        )

        # Requirement 2.3 — SVG must have both w-5 and h-5 classes
        svg_classes = svg.get("class", [])
        assert "w-5" in svg_classes, (
            f"Nav link href='{href}' (role={role}) SVG missing class 'w-5'; "
            f"classes={svg_classes}"
        )
        assert "h-5" in svg_classes, (
            f"Nav link href='{href}' (role={role}) SVG missing class 'h-5'; "
            f"classes={svg_classes}"
        )

        # Requirement 2.2 — no emoji characters in the link's text content
        link_text = link.get_text()
        assert not _has_emoji(link_text), (
            f"Nav link href='{href}' (role={role}) contains emoji in text: "
            f"{link_text!r}"
        )
