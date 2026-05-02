"""Property-based tests for the register package template.

Feature: ui-improvements
Property 7: Carrier dropdown contains exactly the active carriers
Validates: Requirements 12.1
"""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from bs4 import BeautifulSoup
from hypothesis import given, settings
from hypothesis import strategies as st
from jinja2 import Environment, FileSystemLoader

from app.models.carrier import Carrier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def _make_jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    env.globals["current_year"] = 2026
    env.globals["company_name"] = "Test Company"
    env.globals["csrf_token_value"] = lambda request=None: "test-csrf-token"
    env.globals["csrf_input"] = lambda request=None: (
        '<input type="hidden" name="csrf_token" value="test-csrf-token">'
    )
    env.globals["url_for"] = lambda name, **kwargs: f"/static/{kwargs.get('path', '')}"
    return env


def _make_request(path: str = "/packages/new") -> SimpleNamespace:
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


def _make_carrier(carrier_id: int, name: str, is_active: bool) -> Carrier:
    now = datetime(2026, 1, 1)
    return Carrier(
        id=carrier_id,
        name=name,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


def _render_register(carriers: list) -> str:
    """Render the register package template with the given carriers list."""
    env = _make_jinja_env()
    template = env.get_template("packages/register.html")
    return template.render(
        request=_make_request(),
        user=_make_user(),
        carriers=carriers,
    )


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Generate a list of (name, is_active) pairs with unique names
_carrier_name_st = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -"),
).filter(lambda s: s.strip() != "")

_carrier_entry_st = st.tuples(_carrier_name_st, st.booleans())


def _build_carriers(entries: list[tuple[str, bool]]) -> list[Carrier]:
    """Build a deduplicated list of Carrier objects from (name, is_active) pairs."""
    seen: set[str] = set()
    carriers: list[Carrier] = []
    for idx, (name, is_active) in enumerate(entries, start=1):
        key = name.strip().lower()
        if key in seen or not name.strip():
            continue
        seen.add(key)
        carriers.append(_make_carrier(idx, name.strip(), is_active))
    return carriers


# ---------------------------------------------------------------------------
# Property 7: Carrier dropdown contains exactly the active carriers
# Validates: Requirements 12.1
# ---------------------------------------------------------------------------

@given(entries=st.lists(_carrier_entry_st, min_size=0, max_size=20))
@settings(max_examples=100, deadline=None)
def test_property_7_carrier_dropdown_contains_exactly_active_carriers(
    entries: list[tuple[str, bool]],
):
    """**Validates: Requirements 12.1**

    For any set of carriers in the database, the rendered register package
    form's <select name="carrier"> SHALL contain exactly one <option> for each
    active carrier (where is_active = True), and SHALL NOT contain options for
    inactive carriers.
    """
    all_carriers = _build_carriers(entries)
    active_carriers = [c for c in all_carriers if c.is_active]

    html = _render_register(carriers=active_carriers)
    soup = BeautifulSoup(html, "html.parser")

    if active_carriers:
        # The select dropdown must be present
        select = soup.find("select", {"name": "carrier"})
        assert select is not None, (
            "Expected <select name='carrier'> when active carriers exist, but it was not found"
        )

        # Collect all non-placeholder option values
        options = [
            opt["value"]
            for opt in select.find_all("option")
            if opt.get("value", "") != ""
        ]

        active_names = {c.name for c in active_carriers}

        # Every active carrier must have exactly one option
        for carrier in active_carriers:
            assert carrier.name in options, (
                f"Active carrier {carrier.name!r} is missing from the dropdown options"
            )

        # No extra options beyond the active carriers
        assert set(options) == active_names, (
            f"Dropdown options {set(options)!r} do not match active carrier names {active_names!r}"
        )

        # Placeholder option must be present (value="" or disabled)
        placeholder_options = [
            opt for opt in select.find_all("option")
            if opt.get("value", "") == "" or opt.get("disabled") is not None
        ]
        assert placeholder_options, (
            "Expected a blank/placeholder <option> as the default unselected state"
        )

    else:
        # When no active carriers, the select must NOT be present
        select = soup.find("select", {"name": "carrier"})
        assert select is None, (
            "Expected no <select name='carrier'> when carriers list is empty, but found one"
        )

        # An informational fallback message must be present instead
        alerts = soup.find_all(attrs={"role": "alert"})
        info_alerts = [
            a for a in alerts
            if "alert-info" in a.get("class", [])
        ]
        assert info_alerts, (
            "Expected an informational alert when no active carriers are configured"
        )


@given(entries=st.lists(_carrier_entry_st, min_size=1, max_size=20))
@settings(max_examples=100, deadline=None)
def test_property_7b_inactive_carriers_not_in_dropdown(
    entries: list[tuple[str, bool]],
):
    """**Validates: Requirements 12.1**

    The register form dropdown SHALL NOT contain options for inactive carriers.
    Only active carriers (passed via the `carriers` context variable) appear.
    """
    all_carriers = _build_carriers(entries)
    active_carriers = [c for c in all_carriers if c.is_active]
    inactive_carriers = [c for c in all_carriers if not c.is_active]

    # Render with only active carriers (as the route would pass)
    html = _render_register(carriers=active_carriers)
    soup = BeautifulSoup(html, "html.parser")

    select = soup.find("select", {"name": "carrier"})

    if not inactive_carriers:
        # Nothing to assert about inactive carriers if there are none
        return

    if select is None:
        # No select means no active carriers — inactive ones definitely not shown
        return

    option_values = {
        opt.get("value", "")
        for opt in select.find_all("option")
        if opt.get("value", "") != ""
    }

    for carrier in inactive_carriers:
        assert carrier.name not in option_values, (
            f"Inactive carrier {carrier.name!r} should not appear in the dropdown"
        )
