"""Property-based tests for footer copyright format.

Feature: ui-improvements
Property 2: Footer copyright format
Validates: Requirements 3.1, 3.4
"""

import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from bs4 import BeautifulSoup
from hypothesis import given, settings
from hypothesis import strategies as st
from jinja2 import Environment, FileSystemLoader

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def _make_jinja_env(current_year: int, company_name: str) -> Environment:
    """Return a Jinja2 Environment with the given footer globals injected."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    env.globals["current_year"] = current_year
    env.globals["company_name"] = company_name
    env.globals["csrf_token_value"] = lambda request=None: "test-csrf-token"
    env.globals["csrf_input"] = lambda request=None: ""
    env.globals["url_for"] = lambda name, **kwargs: f"/static/{kwargs.get('path', '')}"
    return env


def _make_request(path: str = "/dashboard") -> SimpleNamespace:
    url = SimpleNamespace(path=path)
    return SimpleNamespace(url=url, cookies={}, session={})


def _make_user(role: str = "operator") -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        username="testuser",
        full_name="Test User",
        role=role,
        is_active=True,
    )


def _render_footer_html(current_year: int, company_name: str) -> str:
    """Render base.html with the given year and company name, return full HTML."""
    env = _make_jinja_env(current_year, company_name)
    template = env.get_template("base.html")
    return template.render(
        request=_make_request(),
        user=_make_user(),
        title="Test Page",
    )


def _get_footer_text(html: str) -> str:
    """Parse HTML and return the text content of the <footer> element."""
    soup = BeautifulSoup(html, "html.parser")
    footer = soup.find("footer")
    assert footer is not None, "<footer> element not found in rendered HTML"
    return footer.get_text(separator=" ", strip=True)


# ---------------------------------------------------------------------------
# Property 2: Footer copyright format
# Validates: Requirements 3.1, 3.4
# ---------------------------------------------------------------------------

@given(company_name=st.text(min_size=1, max_size=50, alphabet=st.characters(
    whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
    whitelist_characters=" &-.",
)))
@settings(max_examples=100, deadline=None)
def test_property_2_footer_copyright_format(company_name: str):
    """**Validates: Requirements 3.1, 3.4**

    For any rendered footer HTML with a known company name, the copyright line
    SHALL match the pattern '© {current_year} {company_name}. All rights reserved.'
    where current_year equals datetime.now().year.
    """
    current_year = datetime.now().year
    html = _render_footer_html(current_year, company_name)
    footer_text = _get_footer_text(html)

    # Requirement 3.4 — exact copyright format
    expected = f"© {current_year} {company_name}. All rights reserved."
    assert expected in footer_text, (
        f"Footer copyright line does not match expected format.\n"
        f"Expected to find: {expected!r}\n"
        f"Footer text was:  {footer_text!r}"
    )

    # Requirement 3.1 — year must be the server's current year, not hardcoded
    assert str(current_year) in footer_text, (
        f"Footer does not contain the current year {current_year}.\n"
        f"Footer text was: {footer_text!r}"
    )
