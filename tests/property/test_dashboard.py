"""Property-based tests for dashboard template.

Feature: ui-improvements
Property 3: Stat card "View All" links are non-ghost buttons
Validates: Requirements 5.1, 5.2

Property 4: Status distribution buttons have aria-labels and correct hrefs
Validates: Requirements 6.2, 6.3
"""

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

VALID_STATUSES = [
    "registered",
    "awaiting_pickup",
    "out_for_delivery",
    "delivered",
    "returned",
]


def _make_jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    env.globals["current_year"] = 2026
    env.globals["company_name"] = "Test Company"
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


def _make_stats() -> SimpleNamespace:
    return SimpleNamespace(
        packages_today=5,
        packages_awaiting_pickup=3,
        packages_delivered_today=2,
        total_packages=100,
    )


def _render_dashboard(status_distribution=None, role: str = "operator") -> str:
    if status_distribution is None:
        status_distribution = []
    env = _make_jinja_env()
    template = env.get_template("dashboard/index.html")
    return template.render(
        request=_make_request(),
        user=_make_user(role),
        stats=_make_stats(),
        status_distribution=status_distribution,
        top_recipients=[],
        today="2026-04-12",
    )


# ---------------------------------------------------------------------------
# Property 3: Stat card "View All" links are non-ghost buttons
# Validates: Requirements 5.1, 5.2
# ---------------------------------------------------------------------------

@given(role=st.sampled_from(["operator", "admin", "super_admin"]))
@settings(max_examples=100, deadline=None)
def test_property_3_stat_card_view_all_not_ghost(role: str):
    """**Validates: Requirements 5.1, 5.2**

    For any rendered dashboard stat card, the "View All" link SHALL be an <a>
    element that does NOT have the class btn-ghost, and SHALL have at least one
    of btn-outline or btn-primary.
    """
    html = _render_dashboard(role=role)
    soup = BeautifulSoup(html, "html.parser")

    view_all_links = [
        a for a in soup.find_all("a")
        if a.get_text(strip=True) == "View All"
    ]

    assert len(view_all_links) == 4, (
        f"Expected 4 'View All' links in stat cards, found {len(view_all_links)}"
    )

    for link in view_all_links:
        classes = link.get("class", [])
        assert "btn-ghost" not in classes, (
            f"'View All' link still uses btn-ghost: {link}"
        )
        assert "btn-outline" in classes or "btn-primary" in classes, (
            f"'View All' link lacks btn-outline or btn-primary: {link}"
        )


# ---------------------------------------------------------------------------
# Property 4: Status distribution buttons have aria-labels and correct hrefs
# Validates: Requirements 6.2, 6.3
# ---------------------------------------------------------------------------

@given(status=st.sampled_from(VALID_STATUSES))
@settings(max_examples=100, deadline=None)
def test_property_4_status_distribution_aria_labels(status: str):
    """**Validates: Requirements 6.2, 6.3**

    For any status value in the status distribution list, the corresponding
    navigation button SHALL have a non-empty aria-label attribute AND its href
    SHALL contain /packages?status={status}.
    """
    status_distribution = [SimpleNamespace(status=status, count=7)]
    html = _render_dashboard(status_distribution=status_distribution)
    soup = BeautifulSoup(html, "html.parser")

    # Find the navigation link for this status — must have an aria-label (the
    # stat-card "View All" links share the same href but have no aria-label).
    expected_href = f"/packages?status={status}"
    nav_links = soup.find_all("a", href=expected_href)

    # At least one link with this href must carry an aria-label (the chevron button)
    aria_links = [a for a in nav_links if a.get("aria-label")]
    assert aria_links, (
        f"No <a> with href={expected_href!r} has an aria-label for status {status!r}. "
        f"Found links: {nav_links}"
    )

    nav_link = aria_links[0]
    aria_label = nav_link.get("aria-label", "")
    assert len(aria_label.strip()) > 0, (
        f"Navigation button for status {status!r} has empty aria-label"
    )

    # Verify it contains an SVG (not a raw arrow character)
    svg = nav_link.find("svg")
    assert svg is not None, (
        f"Navigation button for status {status!r} does not contain an SVG icon"
    )
    raw_text = nav_link.get_text(strip=True)
    assert "→" not in raw_text, (
        f"Navigation button for status {status!r} still contains raw '→' character"
    )
