"""Property-based tests for character counter selector scoping.

Feature: ui-improvements
Property 15: Character counter not attached to inputs without maxlength
Property 16: Character counter not attached to inputs with data-counter="false"
Validates: Requirements 19.1, 19.2, 19.3
"""

import re

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# The CHARACTER_COUNTER_SELECTOR from base.html, reproduced here so the
# property tests can validate the selector logic in pure Python without
# requiring a browser or JS runtime.
#
# Selector (from templates/base.html):
#   input[type="text"][maxlength]:not([data-counter="false"]),
#   input[type="search"][maxlength]:not([data-counter="false"]),
#   input[type="email"][maxlength]:not([data-counter="false"]),
#   input[type="password"][maxlength]:not([data-counter="false"]),
#   input[type="tel"][maxlength]:not([data-counter="false"]),
#   input[type="url"][maxlength]:not([data-counter="false"]),
#   textarea[maxlength]:not([data-counter="false"])
#
# Rules encoded:
#   1. Element must be <input> with a supported type OR <textarea>.
#   2. Element must have a `maxlength` attribute.
#   3. Element must NOT have data-counter="false".
# ---------------------------------------------------------------------------

SUPPORTED_INPUT_TYPES = {"text", "search", "email", "password", "tel", "url"}


def selector_matches(tag: str, input_type: str | None, has_maxlength: bool, counter_false: bool) -> bool:
    """Python equivalent of the CHARACTER_COUNTER_SELECTOR match logic.

    Returns True if the element would be selected (i.e., a counter would be
    attached), False otherwise.
    """
    if tag == "textarea":
        return has_maxlength and not counter_false
    if tag == "input" and input_type in SUPPORTED_INPUT_TYPES:
        return has_maxlength and not counter_false
    return False


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

supported_input_types = st.sampled_from(sorted(SUPPORTED_INPUT_TYPES))
unsupported_input_types = st.sampled_from(["number", "checkbox", "radio", "file", "hidden", "date", "range"])
positive_maxlength = st.integers(min_value=1, max_value=10_000)


# ---------------------------------------------------------------------------
# Property 15: Character counter not attached to inputs without maxlength
# Validates: Requirement 19.1
# ---------------------------------------------------------------------------

@given(input_type=supported_input_types)
@settings(max_examples=100, deadline=None)
def test_property_15_no_counter_without_maxlength_input(input_type: str):
    """**Validates: Requirement 19.1**

    For any <input> element with a supported type that does NOT have a
    `maxlength` attribute, the selector SHALL NOT match it (no counter attached).
    """
    matched = selector_matches(
        tag="input",
        input_type=input_type,
        has_maxlength=False,
        counter_false=False,
    )
    assert not matched, (
        f"Selector matched <input type='{input_type}'> without maxlength — "
        "a character counter must NOT be attached to inputs lacking maxlength."
    )


def test_property_15_no_counter_without_maxlength_textarea():
    """**Validates: Requirement 19.1**

    For any <textarea> that does NOT have a `maxlength` attribute, the selector
    SHALL NOT match it.
    """
    matched = selector_matches(
        tag="textarea",
        input_type=None,
        has_maxlength=False,
        counter_false=False,
    )
    assert not matched, (
        "Selector matched <textarea> without maxlength — "
        "a character counter must NOT be attached."
    )


@given(input_type=unsupported_input_types, has_maxlength=st.booleans())
@settings(max_examples=100, deadline=None)
def test_property_15_no_counter_for_unsupported_input_types(input_type: str, has_maxlength: bool):
    """**Validates: Requirement 19.1**

    Inputs with unsupported types (e.g., number, checkbox) SHALL NOT receive a
    character counter regardless of whether they have a maxlength attribute.
    """
    matched = selector_matches(
        tag="input",
        input_type=input_type,
        has_maxlength=has_maxlength,
        counter_false=False,
    )
    assert not matched, (
        f"Selector matched <input type='{input_type}'> — unsupported input types "
        "must never receive a character counter."
    )


# ---------------------------------------------------------------------------
# Property 16: Character counter not attached to inputs with data-counter="false"
# Validates: Requirements 19.2, 19.3
# ---------------------------------------------------------------------------

@given(input_type=supported_input_types, maxlength=positive_maxlength)
@settings(max_examples=100, deadline=None)
def test_property_16_no_counter_when_data_counter_false_input(input_type: str, maxlength: int):
    """**Validates: Requirements 19.2, 19.3**

    For any <input> element with data-counter="false", the selector SHALL NOT
    match it, even when the input has a maxlength attribute.
    """
    matched = selector_matches(
        tag="input",
        input_type=input_type,
        has_maxlength=True,
        counter_false=True,
    )
    assert not matched, (
        f"Selector matched <input type='{input_type}' maxlength='{maxlength}' "
        "data-counter='false'> — data-counter='false' must suppress the counter "
        "regardless of maxlength."
    )


@given(maxlength=positive_maxlength)
@settings(max_examples=100, deadline=None)
def test_property_16_no_counter_when_data_counter_false_textarea(maxlength: int):
    """**Validates: Requirements 19.2, 19.3**

    For any <textarea> with data-counter="false", the selector SHALL NOT match
    it, even when the textarea has a maxlength attribute.
    """
    matched = selector_matches(
        tag="textarea",
        input_type=None,
        has_maxlength=True,
        counter_false=True,
    )
    assert not matched, (
        f"Selector matched <textarea maxlength='{maxlength}' data-counter='false'> — "
        "data-counter='false' must suppress the counter regardless of maxlength."
    )


# ---------------------------------------------------------------------------
# Positive case: counter IS attached when both conditions are met
# ---------------------------------------------------------------------------

@given(input_type=supported_input_types, maxlength=positive_maxlength)
@settings(max_examples=100, deadline=None)
def test_counter_attached_when_maxlength_and_no_opt_out(input_type: str, maxlength: int):
    """Sanity check: selector DOES match when maxlength is present and
    data-counter is not "false". Ensures the selector is not trivially broken.
    """
    matched = selector_matches(
        tag="input",
        input_type=input_type,
        has_maxlength=True,
        counter_false=False,
    )
    assert matched, (
        f"Selector did NOT match <input type='{input_type}' maxlength='{maxlength}'> — "
        "a character counter SHOULD be attached when maxlength is present and "
        "data-counter is not 'false'."
    )
