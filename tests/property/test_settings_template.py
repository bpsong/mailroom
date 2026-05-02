"""Property-based tests for the admin settings template.

Feature: ui-improvements
Property 9: Admin settings displays all carriers
Validates: Requirements 13.2
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


def _make_request(path: str = "/admin/settings") -> SimpleNamespace:
    url = SimpleNamespace(path=path)
    return SimpleNamespace(url=url, cookies={}, session={})


def _make_user(role: str = "super_admin") -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        username="admin",
        full_name="Admin User",
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


def _find_row_for_carrier(rows, carrier_name: str):
    """Find the table row whose first <td> exactly matches the carrier name."""
    for row in rows:
        cells = row.find_all("td")
        if cells and cells[0].get_text(strip=True) == carrier_name:
            return row
    return None


def _render_settings(carriers: list) -> str:
    """Render the admin settings template with the given carriers list."""
    env = _make_jinja_env()
    template = env.get_template("admin/settings.html")
    return template.render(
        request=_make_request(),
        user=_make_user(),
        qr_base_url="",
        carriers=carriers,
    )


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

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
# Property 9: Admin settings displays all carriers
# Validates: Requirements 13.2
# ---------------------------------------------------------------------------

@given(entries=st.lists(_carrier_entry_st, min_size=0, max_size=20))
@settings(max_examples=100, deadline=None)
def test_property_9_admin_settings_displays_all_carriers(
    entries: list[tuple[str, bool]],
):
    """**Validates: Requirements 13.2**

    For any set of carriers (active and inactive) in the database, the rendered
    admin settings carriers section SHALL display a row for every carrier
    regardless of its `is_active` status.
    """
    all_carriers = _build_carriers(entries)

    html = _render_settings(carriers=all_carriers)
    soup = BeautifulSoup(html, "html.parser")

    if all_carriers:
        # The carriers table must be present
        table = soup.find("table")
        assert table is not None, (
            "Expected a <table> in the carriers section when carriers exist, but none was found"
        )

        # Collect all table row cells in the tbody
        tbody = table.find("tbody")
        assert tbody is not None, "Expected a <tbody> in the carriers table"

        rows = tbody.find_all("tr")
        assert len(rows) == len(all_carriers), (
            f"Expected {len(all_carriers)} table rows but found {len(rows)}. "
            f"All carriers (active and inactive) must be displayed."
        )

        # Every carrier name must appear in the table — use exact first-cell match
        for carrier in all_carriers:
            carrier_row = _find_row_for_carrier(rows, carrier.name)
            assert carrier_row is not None, (
                f"Carrier {carrier.name!r} (is_active={carrier.is_active}) "
                f"is missing from the carriers table"
            )

        # Active carriers must show an "Active" badge
        active_carriers = [c for c in all_carriers if c.is_active]
        for carrier in active_carriers:
            carrier_row = _find_row_for_carrier(rows, carrier.name)
            assert carrier_row is not None, (
                f"Could not find table row for carrier {carrier.name!r}"
            )
            badges = carrier_row.find_all(class_=lambda c: c and "badge" in c)
            badge_texts = [b.get_text(strip=True) for b in badges]
            assert any("Active" in t for t in badge_texts), (
                f"Active carrier {carrier.name!r} should show an 'Active' badge, "
                f"but badges found: {badge_texts}"
            )

        # Inactive carriers must show an "Inactive" badge
        inactive_carriers = [c for c in all_carriers if not c.is_active]
        for carrier in inactive_carriers:
            carrier_row = _find_row_for_carrier(rows, carrier.name)
            assert carrier_row is not None, (
                f"Could not find table row for carrier {carrier.name!r}"
            )
            badges = carrier_row.find_all(class_=lambda c: c and "badge" in c)
            badge_texts = [b.get_text(strip=True) for b in badges]
            assert any("Inactive" in t for t in badge_texts), (
                f"Inactive carrier {carrier.name!r} should show an 'Inactive' badge, "
                f"but badges found: {badge_texts}"
            )

    else:
        # When no carriers, the table must NOT be present
        table = soup.find("table")
        assert table is None, (
            "Expected no <table> when carriers list is empty, but found one"
        )

        # An informational alert must be present instead
        alerts = soup.find_all(attrs={"role": "alert"})
        info_alerts = [
            a for a in alerts
            if "alert-info" in a.get("class", [])
        ]
        assert info_alerts, (
            "Expected an informational alert when no carriers are configured"
        )


@given(entries=st.lists(_carrier_entry_st, min_size=1, max_size=20))
@settings(max_examples=100, deadline=None)
def test_property_9b_deactivate_button_only_for_active_carriers(
    entries: list[tuple[str, bool]],
):
    """**Validates: Requirements 13.2, 13.5**

    The deactivate action button SHALL only appear for active carriers.
    Inactive carriers SHALL NOT have a deactivate button.
    """
    all_carriers = _build_carriers(entries)

    html = _render_settings(carriers=all_carriers)
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")
    if table is None:
        # No table means no carriers — nothing to assert
        return

    tbody = table.find("tbody")
    if tbody is None:
        return

    rows = tbody.find_all("tr")

    for carrier in all_carriers:
        carrier_row = _find_row_for_carrier(rows, carrier.name)
        if carrier_row is None:
            continue

        # Find deactivate buttons in this row
        deactivate_buttons = [
            btn for btn in carrier_row.find_all("button")
            if "Deactivate" in btn.get_text()
        ]

        if carrier.is_active:
            assert deactivate_buttons, (
                f"Active carrier {carrier.name!r} should have a Deactivate button"
            )
        else:
            assert not deactivate_buttons, (
                f"Inactive carrier {carrier.name!r} should NOT have a Deactivate button"
            )


@given(entries=st.lists(_carrier_entry_st, min_size=1, max_size=20))
@settings(max_examples=100, deadline=None)
def test_property_9c_add_carrier_form_always_present(
    entries: list[tuple[str, bool]],
):
    """**Validates: Requirements 13.3**

    The 'Add Carrier' form SHALL always be present on the settings page,
    regardless of how many carriers exist.
    """
    all_carriers = _build_carriers(entries)

    html = _render_settings(carriers=all_carriers)
    soup = BeautifulSoup(html, "html.parser")

    # The add carrier form posts to /admin/carriers
    add_form = soup.find("form", {"action": "/admin/carriers"})
    assert add_form is not None, (
        "Expected an 'Add Carrier' form posting to /admin/carriers, but none was found"
    )

    # The form must have a name input
    name_input = add_form.find("input", {"name": "name"})
    assert name_input is not None, (
        "Expected a <input name='name'> in the Add Carrier form"
    )

    # The form must have a submit button
    submit_btn = add_form.find("button", {"type": "submit"})
    assert submit_btn is not None, (
        "Expected a submit button in the Add Carrier form"
    )
