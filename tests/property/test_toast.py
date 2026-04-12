"""Property-based tests for toast notification deduplication and limit.

Feature: ui-improvements
Property 17: Toast container never exceeds 3 simultaneous notifications
Property 18: Duplicate toast messages are not added
Validates: Requirements 20.1, 20.2, 20.3, 20.4
"""

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Python model of the showToast logic from templates/base.html
#
# The JS implementation:
#   1. Deduplication: if a toast with the same text is already visible, skip.
#   2. Max-3 cap: if there are already 3 toasts, remove the oldest before adding.
#   3. Append the new toast to the container.
#
# We model the toast container as a plain list of message strings (ordered
# oldest-first), which is sufficient to verify both properties without a
# browser or JS runtime.
# ---------------------------------------------------------------------------

MAX_TOASTS = 3


def show_toast(container: list[str], message: str) -> list[str]:
    """Python equivalent of the showToast JS function.

    Returns a new container list after applying deduplication and the max-3 cap.
    The input list is not mutated.
    """
    # Deduplication: skip if identical message already visible
    if message in container:
        return list(container)

    result = list(container)

    # Max-3 cap: remove oldest if at the limit
    if len(result) >= MAX_TOASTS:
        result.pop(0)

    result.append(message)
    return result


def apply_sequence(messages: list[str]) -> list[str]:
    """Apply a sequence of showToast calls and return the final container."""
    container: list[str] = []
    for msg in messages:
        container = show_toast(container, msg)
    return container


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Non-empty strings to use as toast messages
toast_message = st.text(min_size=1, max_size=200)

# Sequences of at least 4 messages to exercise the cap
long_sequence = st.lists(toast_message, min_size=4, max_size=20)

# Sequences of any length (including empty)
any_sequence = st.lists(toast_message, min_size=0, max_size=20)


# ---------------------------------------------------------------------------
# Property 17: Toast container never exceeds 3 simultaneous notifications
# Validates: Requirements 20.1, 20.2
# ---------------------------------------------------------------------------

@given(messages=long_sequence)
@settings(max_examples=100, deadline=None)
def test_property_17_toast_container_never_exceeds_3(messages: list[str]):
    """**Validates: Requirements 20.1, 20.2**

    For any sequence of showToast calls, the number of toast elements in the
    container SHALL NOT exceed 3 at any point in time.
    """
    container: list[str] = []
    for msg in messages:
        container = show_toast(container, msg)
        assert len(container) <= MAX_TOASTS, (
            f"Toast container exceeded {MAX_TOASTS} items after adding '{msg}'. "
            f"Container: {container}"
        )


@given(messages=any_sequence)
@settings(max_examples=100, deadline=None)
def test_property_17_final_container_never_exceeds_3(messages: list[str]):
    """**Validates: Requirements 20.1, 20.2**

    The final container state after any sequence of showToast calls SHALL
    contain at most 3 toasts.
    """
    container = apply_sequence(messages)
    assert len(container) <= MAX_TOASTS, (
        f"Final toast container has {len(container)} items (max {MAX_TOASTS}). "
        f"Messages: {messages}, Container: {container}"
    )


@given(
    initial=st.lists(toast_message, min_size=3, max_size=3),
    new_message=toast_message,
)
@settings(max_examples=100, deadline=None)
def test_property_17_oldest_removed_when_at_cap(initial: list[str], new_message: str):
    """**Validates: Requirements 20.1, 20.2**

    When the container is at the 3-toast limit and a new (non-duplicate) toast
    is added, the oldest toast SHALL be removed to make room.
    """
    # Ensure new_message is not already in the container to avoid dedup path
    # Use a message guaranteed to be distinct
    distinct_initial = list(dict.fromkeys(initial))[:3]  # deduplicate, keep up to 3
    if len(distinct_initial) < 3:
        # Pad with known-unique messages if dedup reduced the list
        for i in range(3 - len(distinct_initial)):
            distinct_initial.append(f"__unique_pad_{i}__")

    unique_new = new_message
    while unique_new in distinct_initial:
        unique_new = unique_new + "_x"

    container = apply_sequence(distinct_initial)
    assert len(container) == 3

    oldest = container[0]
    container = show_toast(container, unique_new)

    assert len(container) == MAX_TOASTS, (
        f"Container size should remain {MAX_TOASTS} after adding to a full container."
    )
    assert oldest not in container, (
        f"Oldest toast '{oldest}' should have been removed when cap was exceeded."
    )
    assert unique_new in container, (
        f"New toast '{unique_new}' should be present after being added."
    )


# ---------------------------------------------------------------------------
# Property 18: Duplicate toast messages are not added
# Validates: Requirements 20.3, 20.4
# ---------------------------------------------------------------------------

@given(message=toast_message, extra=st.lists(toast_message, min_size=0, max_size=2))
@settings(max_examples=100, deadline=None)
def test_property_18_duplicate_not_added(message: str, extra: list[str]):
    """**Validates: Requirements 20.3, 20.4**

    When a toast with an identical message is already visible, calling
    showToast with the same message SHALL NOT increase the container size.
    """
    # Build a container that already contains `message`
    container = show_toast([], message)
    # Optionally add a few other distinct messages
    for m in extra:
        if m != message:
            container = show_toast(container, m)

    size_before = len(container)
    container_after = show_toast(container, message)
    size_after = len(container_after)

    assert size_after == size_before, (
        f"Duplicate toast '{message}' increased container size from "
        f"{size_before} to {size_after}. Container: {container_after}"
    )


@given(message=toast_message)
@settings(max_examples=100, deadline=None)
def test_property_18_duplicate_count_stays_at_one(message: str):
    """**Validates: Requirements 20.3, 20.4**

    Calling showToast with the same message multiple times SHALL result in
    exactly one instance of that message in the container.
    """
    container: list[str] = []
    for _ in range(5):
        container = show_toast(container, message)

    count = container.count(message)
    assert count == 1, (
        f"Message '{message}' appears {count} times in container after 5 calls — "
        "deduplication must ensure at most one instance."
    )


@given(messages=long_sequence)
@settings(max_examples=100, deadline=None)
def test_property_18_no_duplicates_in_container_at_any_point(messages: list[str]):
    """**Validates: Requirements 20.3, 20.4**

    At no point during a sequence of showToast calls SHALL the container
    contain two toasts with identical message text.
    """
    container: list[str] = []
    for msg in messages:
        container = show_toast(container, msg)
        assert len(container) == len(set(container)), (
            f"Duplicate messages found in container after adding '{msg}'. "
            f"Container: {container}"
        )


# ---------------------------------------------------------------------------
# Positive / sanity checks
# ---------------------------------------------------------------------------

@given(messages=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=3))
@settings(max_examples=100, deadline=None)
def test_distinct_messages_within_cap_all_appear(messages: list[str]):
    """Sanity check: up to 3 distinct messages are all present in the container."""
    distinct = list(dict.fromkeys(messages))[:3]
    container = apply_sequence(distinct)
    for msg in distinct:
        assert msg in container, (
            f"Message '{msg}' should be in container {container} after being added."
        )
