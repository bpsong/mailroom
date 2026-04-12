"""Property-based tests for package detail template.

Feature: ui-improvements
Property 6: Status timeline visual distinction
Validates: Requirements 10.1, 10.2, 10.3
"""

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


def _make_request(path: str = "/packages/1") -> SimpleNamespace:
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


def _make_timeline_event(new_status: str, notes: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        new_status=new_status,
        notes=notes,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
    )


def _make_package(status: str, timeline: list) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        tracking_no="TRK-001",
        carrier="UPS",
        status=status,
        recipient_name="Jane Doe",
        recipient_email="jane@example.com",
        recipient_department="Engineering",
        notes="",
        created_by_name="Admin",
        created_at=datetime(2026, 1, 1, 10, 0, 0),
        updated_at=datetime(2026, 1, 1, 12, 0, 0),
        timeline=timeline,
    )


def _render_detail(package, attachments=None) -> str:
    if attachments is None:
        attachments = []
    env = _make_jinja_env()
    template = env.get_template("packages/detail.html")
    return template.render(
        request=_make_request(),
        user=_make_user(),
        package=package,
        attachments=attachments,
        qr_code_data="",
    )


# ---------------------------------------------------------------------------
# Strategy: generate a non-empty list of timeline events
# ---------------------------------------------------------------------------

@st.composite
def timeline_events(draw):
    statuses = draw(
        st.lists(
            st.sampled_from(VALID_STATUSES),
            min_size=1,
            max_size=5,
        )
    )
    return [_make_timeline_event(s) for s in statuses]


# ---------------------------------------------------------------------------
# Property 6: Status timeline visual distinction
# Validates: Requirements 10.1, 10.2, 10.3
# ---------------------------------------------------------------------------

@given(events=timeline_events())
@settings(max_examples=100, deadline=None)
def test_property_6_timeline_visual_distinction(events):
    """**Validates: Requirements 10.1, 10.2, 10.3**

    For any package with at least one timeline event:
    - The last timeline step SHALL have class step-primary.
    - All preceding steps SHALL have class step-neutral.
    - No two steps share step-primary simultaneously (unless there is only one step).
    """
    last_status = events[-1].new_status
    package = _make_package(status=last_status, timeline=events)
    html = _render_detail(package)
    soup = BeautifulSoup(html, "html.parser")

    timeline_ul = soup.find("ul", id="package-timeline")
    assert timeline_ul is not None, "Could not find <ul id='package-timeline'>"

    steps = timeline_ul.find_all("li", class_="step")
    assert len(steps) == len(events), (
        f"Expected {len(events)} timeline steps, found {len(steps)}"
    )

    if len(steps) == 1:
        # Single step must be step-primary
        classes = steps[0].get("class", [])
        assert "step-primary" in classes, (
            f"Single timeline step should be step-primary, got classes: {classes}"
        )
    else:
        # Last step must be step-primary
        last_classes = steps[-1].get("class", [])
        assert "step-primary" in last_classes, (
            f"Last timeline step should be step-primary, got classes: {last_classes}"
        )
        assert "step-neutral" not in last_classes, (
            f"Last timeline step should not be step-neutral, got classes: {last_classes}"
        )

        # All preceding steps must be step-neutral, not step-primary
        for i, step in enumerate(steps[:-1]):
            classes = step.get("class", [])
            assert "step-neutral" in classes, (
                f"Step {i} (not last) should be step-neutral, got classes: {classes}"
            )
            assert "step-primary" not in classes, (
                f"Step {i} (not last) should not be step-primary, got classes: {classes}"
            )
