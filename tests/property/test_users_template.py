"""Property-based tests for the admin users list template.

Feature: ui-improvements
Property 13: Three-dot menu buttons have user-specific aria-labels
Validates: Requirements 15.1, 15.2
"""

from pathlib import Path
from types import SimpleNamespace

from bs4 import BeautifulSoup
from hypothesis import given, settings
from hypothesis import strategies as st
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def _make_jinja_env():
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


def _make_request(path="/admin/users"):
    url = SimpleNamespace(path=path)
    return SimpleNamespace(url=url, cookies={}, session={})


def _make_pagination(total=0):
    return SimpleNamespace(total=total, limit=50, offset=0, has_more=False)


def _make_user_item(user_id, username, role="operator", is_active=True, current_user_id=999):
    """Build a user row item that is manageable by a super_admin."""
    return SimpleNamespace(
        id=user_id,
        username=username,
        full_name=f"User {username}",
        role=role,
        is_active=is_active,
        must_change_password=False,
        created_at=None,
    )


def _render_users_list(users, current_user_role="super_admin", current_user_id=999):
    current_user = SimpleNamespace(
        id=current_user_id,
        username="admin",
        full_name="Admin User",
        role=current_user_role,
        is_active=True,
    )
    env = _make_jinja_env()
    template = env.get_template("admin/users_list.html")
    return template.render(
        request=_make_request(),
        user=current_user,
        users=users,
        pagination=_make_pagination(total=len(users)),
        query="",
        role="",
        is_active="",
    )


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_username_st = st.text(
    min_size=1,
    max_size=30,
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="_-",
    ),
).filter(lambda s: s.strip() != "")


def _build_users(usernames):
    """Build a list of unique user items from a list of usernames."""
    seen = set()
    result = []
    for idx, username in enumerate(usernames, start=1):
        key = username.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(_make_user_item(user_id=idx, username=username, role="operator"))
    return result


# ---------------------------------------------------------------------------
# Property 13: Three-dot menu buttons have user-specific aria-labels
# Validates: Requirements 15.1, 15.2
# ---------------------------------------------------------------------------

@given(usernames=st.lists(_username_st, min_size=1, max_size=10))
@settings(max_examples=100, deadline=None)
def test_property_13_three_dot_menu_aria_labels(usernames):
    """**Validates: Requirements 15.1, 15.2**

    For any user row rendered in the user management table where the current
    user has management access (super_admin viewing operators), the three-dot
    menu trigger button SHALL have an aria-label attribute whose value contains
    the target user's username.
    """
    users = _build_users(usernames)
    if not users:
        return

    html = _render_users_list(users, current_user_role="super_admin", current_user_id=999)
    soup = BeautifulSoup(html, "html.parser")

    for user_item in users:
        # Find the label element that serves as the three-dot menu trigger for this user.
        # Match on the exact aria-label value to avoid substring collisions.
        expected_aria = f"Actions for {user_item.username}"

        # Search all <label> elements with an aria-label matching exactly
        matching_labels = soup.find_all(
            "label",
            attrs={"aria-label": expected_aria},
        )

        assert matching_labels, (
            f"No three-dot menu trigger found with aria-label='{expected_aria}'. "
            f"Expected aria-label='Actions for {user_item.username}'"
        )

        label = matching_labels[0]
        aria_label = label.get("aria-label", "")

        assert aria_label == expected_aria, (
            f"aria-label {aria_label!r} does not equal expected {expected_aria!r}"
        )

        # The label must NOT rely solely on the SVG — the aria-label must be non-empty text
        assert aria_label.strip() != "", (
            f"aria-label for user {user_item.username!r} is empty"
        )

        # The label must contain an SVG icon (the three-dot icon)
        svg = label.find("svg")
        assert svg is not None, (
            f"Three-dot menu trigger for {user_item.username!r} is missing its SVG icon"
        )


@given(usernames=st.lists(_username_st, min_size=1, max_size=5))
@settings(max_examples=50, deadline=None)
def test_property_13b_aria_label_unique_per_user(usernames):
    """**Validates: Requirements 15.1, 15.2**

    Each three-dot menu trigger SHALL have a distinct aria-label that uniquely
    identifies the target user, so screen reader users can distinguish between
    action menus for different users.
    """
    users = _build_users(usernames)
    if len(users) < 2:
        return

    html = _render_users_list(users, current_user_role="super_admin", current_user_id=999)
    soup = BeautifulSoup(html, "html.parser")

    aria_labels = [
        label.get("aria-label", "")
        for label in soup.find_all("label", attrs={"aria-label": True})
        if label.get("aria-label", "").startswith("Actions for")
    ]

    # All aria-labels must be unique (one per user)
    assert len(aria_labels) == len(set(aria_labels)), (
        f"Duplicate aria-labels found among three-dot menus: {aria_labels}"
    )

    # Each user's username must appear in exactly one aria-label.
    # Use exact equality "Actions for {username}" to avoid substring collisions
    # (e.g. username "c" would match inside "Actions" via naive substring check).
    for user_item in users:
        expected = f"Actions for {user_item.username}"
        matching = [lbl for lbl in aria_labels if lbl == expected]
        assert len(matching) == 1, (
            f"Expected exactly 1 aria-label equal to {expected!r}, "
            f"found {len(matching)}: {matching}"
        )
