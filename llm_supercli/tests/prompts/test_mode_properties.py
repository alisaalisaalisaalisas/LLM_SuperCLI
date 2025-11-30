"""
Property-based tests for mode management.

Tests correctness properties defined in the design document using hypothesis.
"""

import pytest
from hypothesis import given, settings, strategies as st, assume

from llm_supercli.prompts.modes import (
    ModeConfig,
    validate_mode_config,
    VALID_TOOL_GROUPS,
)


# Strategies for generating test data

def valid_slug_strategy():
    """Generate valid slugs: start with lowercase letter, then lowercase/digits/hyphens."""
    return st.from_regex(r"^[a-z][a-z0-9-]{0,20}$", fullmatch=True)


def invalid_slug_strategy():
    """Generate invalid slugs that should fail validation."""
    return st.one_of(
        # Starts with number
        st.from_regex(r"^[0-9][a-z0-9-]*$", fullmatch=True),
        # Starts with hyphen
        st.from_regex(r"^-[a-z0-9-]*$", fullmatch=True),
        # Contains uppercase
        st.from_regex(r"^[a-z][a-zA-Z0-9-]*[A-Z][a-zA-Z0-9-]*$", fullmatch=True),
        # Empty string
        st.just(""),
    )


def valid_name_strategy():
    """Generate valid names (non-empty, max 100 chars)."""
    return st.text(min_size=1, max_size=100)


def valid_role_definition_strategy():
    """Generate valid role definitions (min 10 chars)."""
    return st.text(min_size=10, max_size=500)


def valid_tool_groups_strategy():
    """Generate valid tool groups lists."""
    return st.lists(
        st.sampled_from(list(VALID_TOOL_GROUPS)),
        max_size=len(VALID_TOOL_GROUPS),
    )


def valid_icon_strategy():
    """Generate valid icons (max 4 chars)."""
    return st.text(min_size=0, max_size=4)


@st.composite
def valid_mode_config_dict(draw):
    """Generate a valid mode configuration dictionary."""
    return {
        "slug": draw(valid_slug_strategy()),
        "name": draw(valid_name_strategy()),
        "role_definition": draw(valid_role_definition_strategy()),
        "base_instructions": draw(st.text(max_size=200)),
        "tool_groups": draw(valid_tool_groups_strategy()),
        "icon": draw(valid_icon_strategy()),
    }


@st.composite
def invalid_mode_config_missing_required(draw):
    """Generate mode config dicts missing required fields."""
    # Start with a valid config
    config = draw(valid_mode_config_dict())
    
    # Remove one or more required fields
    required_fields = ["slug", "name", "role_definition"]
    fields_to_remove = draw(st.lists(
        st.sampled_from(required_fields),
        min_size=1,
        max_size=3,
        unique=True,
    ))
    
    for field in fields_to_remove:
        del config[field]
    
    return config


@st.composite
def invalid_mode_config_wrong_types(draw):
    """Generate mode config dicts with wrong field types."""
    config = draw(valid_mode_config_dict())
    
    # Pick a field to corrupt
    field_to_corrupt = draw(st.sampled_from([
        "slug", "name", "role_definition", "base_instructions", "tool_groups", "icon"
    ]))
    
    # Replace with wrong type
    if field_to_corrupt == "tool_groups":
        # Should be array, make it a string
        config[field_to_corrupt] = "not-an-array"
    else:
        # Should be string, make it a number or list
        config[field_to_corrupt] = draw(st.one_of(
            st.integers(),
            st.lists(st.integers(), min_size=1, max_size=3),
        ))
    
    return config


# **Feature: prompt-system-refactor, Property 4: Mode schema validation**
@settings(max_examples=100)
@given(config=valid_mode_config_dict())
def test_valid_mode_configs_accepted(config: dict):
    """
    Property 4: Mode schema validation (valid configs accepted)
    
    For any mode configuration dictionary that has all required fields
    (slug, name, role_definition) with valid types, validation SHALL accept
    the configuration.
    
    **Validates: Requirements 2.3**
    """
    is_valid, errors = validate_mode_config(config)
    
    assert is_valid, f"Valid config should be accepted, but got errors: {errors}"
    assert errors == [], f"Valid config should have no errors, but got: {errors}"


# **Feature: prompt-system-refactor, Property 4: Mode schema validation**
@settings(max_examples=100)
@given(config=invalid_mode_config_missing_required())
def test_missing_required_fields_rejected(config: dict):
    """
    Property 4: Mode schema validation (missing required fields rejected)
    
    For any mode configuration dictionary missing required fields,
    validation SHALL reject the configuration.
    
    **Validates: Requirements 2.3**
    """
    is_valid, errors = validate_mode_config(config)
    
    assert not is_valid, "Config missing required fields should be rejected"
    assert len(errors) > 0, "Should have at least one error message"
    
    # Check that error mentions missing field
    error_text = " ".join(errors).lower()
    assert "missing" in error_text or "required" in error_text, (
        f"Error should mention missing/required field: {errors}"
    )


# **Feature: prompt-system-refactor, Property 4: Mode schema validation**
@settings(max_examples=100)
@given(config=invalid_mode_config_wrong_types())
def test_wrong_types_rejected(config: dict):
    """
    Property 4: Mode schema validation (wrong types rejected)
    
    For any mode configuration dictionary with invalid types,
    validation SHALL reject the configuration.
    
    **Validates: Requirements 2.3**
    """
    is_valid, errors = validate_mode_config(config)
    
    assert not is_valid, f"Config with wrong types should be rejected: {config}"
    assert len(errors) > 0, "Should have at least one error message"


# **Feature: prompt-system-refactor, Property 4: Mode schema validation**
@settings(max_examples=100)
@given(
    valid_config=valid_mode_config_dict(),
    invalid_tool_group=st.text(min_size=1, max_size=20).filter(
        lambda x: x not in VALID_TOOL_GROUPS
    )
)
def test_invalid_tool_groups_rejected(valid_config: dict, invalid_tool_group: str):
    """
    Property 4: Mode schema validation (invalid tool groups rejected)
    
    For any mode configuration with tool_groups containing invalid values,
    validation SHALL reject the configuration.
    
    **Validates: Requirements 2.3**
    """
    # Add an invalid tool group
    valid_config["tool_groups"] = [invalid_tool_group]
    
    is_valid, errors = validate_mode_config(valid_config)
    
    assert not is_valid, f"Config with invalid tool group '{invalid_tool_group}' should be rejected"
    assert len(errors) > 0, "Should have at least one error message"
    
    # Check that error mentions the invalid value
    error_text = " ".join(errors).lower()
    assert "tool_groups" in error_text or "invalid" in error_text, (
        f"Error should mention tool_groups or invalid: {errors}"
    )


# **Feature: prompt-system-refactor, Property 4: Mode schema validation**
@settings(max_examples=100)
@given(slug=invalid_slug_strategy())
def test_invalid_slug_pattern_rejected(slug: str):
    """
    Property 4: Mode schema validation (invalid slug pattern rejected)
    
    For any mode configuration with a slug that doesn't match the required
    pattern (lowercase letter followed by lowercase/digits/hyphens),
    validation SHALL reject the configuration.
    
    **Validates: Requirements 2.3**
    """
    config = {
        "slug": slug,
        "name": "Test Mode",
        "role_definition": "A test mode for validation testing",
    }
    
    is_valid, errors = validate_mode_config(config)
    
    assert not is_valid, f"Config with invalid slug '{slug}' should be rejected"
    assert len(errors) > 0, "Should have at least one error message"
