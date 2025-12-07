"""
Property-based tests for prompt configuration.

Tests correctness properties defined in the design document using hypothesis.
"""

import allure
import pytest
from hypothesis import given, settings, strategies as st, assume

from llm_supercli.prompts.config import (
    PromptConfig,
    export_config,
    import_config,
    validate_config,
    ConfigError,
    CONFIG_VERSION,
)


# Strategies for generating test data

@st.composite
def valid_mode_slug_strategy(draw):
    """Generate valid mode slugs (lowercase letters, numbers, hyphens)."""
    first_char = draw(st.sampled_from("abcdefghijklmnopqrstuvwxyz"))
    rest = draw(st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
        min_size=0,
        max_size=20
    ))
    return first_char + rest


@st.composite
def variable_dict_strategy(draw):
    """Generate a dictionary of string variables."""
    # Generate keys that are valid identifiers
    keys = draw(st.lists(
        st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz_"),
            min_size=1,
            max_size=20
        ),
        min_size=0,
        max_size=5,
        unique=True
    ))
    
    values = draw(st.lists(
        st.text(min_size=0, max_size=50),
        min_size=len(keys),
        max_size=len(keys)
    ))
    
    return dict(zip(keys, values))


@st.composite
def prompt_config_strategy(draw):
    """Generate valid PromptConfig objects."""
    mode = draw(valid_mode_slug_strategy())
    include_tools = draw(st.booleans())
    include_mcp = draw(st.booleans())
    
    # Custom instructions can be None or a string
    custom_instructions = draw(st.one_of(
        st.none(),
        st.text(min_size=0, max_size=100)
    ))
    
    variables = draw(variable_dict_strategy())
    
    return PromptConfig(
        mode=mode,
        include_tools=include_tools,
        include_mcp=include_mcp,
        custom_instructions=custom_instructions,
        variables=variables,
    )


# **Feature: prompt-system-refactor, Property 8: Configuration round-trip consistency**
@allure.feature("Prompt Configuration")
@allure.story("Configuration round-trip consistency")
@allure.severity(allure.severity_level.CRITICAL)
@settings(max_examples=100)
@given(config=prompt_config_strategy())
def test_config_round_trip_consistency(config: PromptConfig):
    """
    Property 8: Configuration round-trip consistency
    
    For any valid PromptConfig object, serializing to JSON and deserializing
    back SHALL produce a PromptConfig that is equivalent to the original
    (same mode, same section settings, same variables).
    
    **Validates: Requirements 8.1, 8.2**
    """
    # Export to JSON
    json_str = export_config(config)
    
    # Import back from JSON
    restored_config = import_config(json_str)
    
    # Verify equivalence
    assert restored_config.mode == config.mode, (
        f"Mode mismatch: expected '{config.mode}', got '{restored_config.mode}'"
    )
    assert restored_config.include_tools == config.include_tools, (
        f"include_tools mismatch: expected {config.include_tools}, "
        f"got {restored_config.include_tools}"
    )
    assert restored_config.include_mcp == config.include_mcp, (
        f"include_mcp mismatch: expected {config.include_mcp}, "
        f"got {restored_config.include_mcp}"
    )
    assert restored_config.custom_instructions == config.custom_instructions, (
        f"custom_instructions mismatch: expected '{config.custom_instructions}', "
        f"got '{restored_config.custom_instructions}'"
    )
    assert restored_config.variables == config.variables, (
        f"variables mismatch: expected {config.variables}, "
        f"got {restored_config.variables}"
    )
    
    # Also verify using __eq__
    assert restored_config == config, "Restored config should equal original"


# Additional tests for validation and error handling

@allure.feature("Prompt Configuration")
@allure.story("Import malformed JSON error reporting")
@allure.severity(allure.severity_level.NORMAL)
def test_import_malformed_json_reports_line_column():
    """Test that malformed JSON reports line and column information."""
    malformed_json = '{\n  "version": "1.0",\n  "mode": invalid\n}'
    
    with pytest.raises(ConfigError) as exc_info:
        import_config(malformed_json)
    
    error = exc_info.value
    assert error.line is not None, "Error should include line number"
    assert error.column is not None, "Error should include column number"


@allure.feature("Prompt Configuration")
@allure.story("Import validation - missing version")
@allure.severity(allure.severity_level.NORMAL)
def test_import_missing_version_fails_validation():
    """Test that missing version field fails validation."""
    json_str = '{"mode": "code"}'
    
    with pytest.raises(ConfigError) as exc_info:
        import_config(json_str)
    
    assert "version" in str(exc_info.value).lower()


@allure.feature("Prompt Configuration")
@allure.story("Export includes version")
@allure.severity(allure.severity_level.NORMAL)
def test_export_includes_version():
    """Test that exported config includes version."""
    config = PromptConfig()
    json_str = export_config(config)
    
    assert f'"version": "{CONFIG_VERSION}"' in json_str


@allure.feature("Prompt Configuration")
@allure.story("Validation accepts valid config")
@allure.severity(allure.severity_level.NORMAL)
def test_validate_config_accepts_valid_config():
    """Test that validation accepts a valid configuration."""
    valid_config = {
        "version": "1.0",
        "mode": "code",
        "include_tools": True,
        "include_mcp": False,
        "custom_instructions": "Be helpful",
        "variables": {"name": "test"},
    }
    
    is_valid, errors = validate_config(valid_config)
    assert is_valid, f"Valid config should pass validation: {errors}"
    assert len(errors) == 0


@allure.feature("Prompt Configuration")
@allure.story("Validation rejects invalid types")
@allure.severity(allure.severity_level.NORMAL)
def test_validate_config_rejects_invalid_types():
    """Test that validation rejects invalid field types."""
    invalid_config = {
        "version": "1.0",
        "mode": 123,  # Should be string
        "include_tools": "yes",  # Should be boolean
    }
    
    is_valid, errors = validate_config(invalid_config)
    assert not is_valid, "Invalid config should fail validation"
    assert len(errors) > 0


@allure.feature("Prompt Configuration")
@allure.story("Validation rejects invalid variables")
@allure.severity(allure.severity_level.NORMAL)
def test_validate_config_rejects_invalid_variables():
    """Test that validation rejects non-string variable values."""
    invalid_config = {
        "version": "1.0",
        "variables": {"count": 42},  # Value should be string
    }
    
    is_valid, errors = validate_config(invalid_config)
    assert not is_valid, "Config with non-string variable should fail"
    assert any("variable" in e.lower() for e in errors)
