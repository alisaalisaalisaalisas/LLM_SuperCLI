"""
Property-based tests for ContextBuilder and variable interpolation.

Tests correctness properties defined in the design document using hypothesis.
"""

import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st, assume

from llm_supercli.prompts.context import ContextBuilder, interpolate, VariableError


# Windows reserved device names that cannot be used as directory names
WINDOWS_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
}


def is_valid_dirname(name: str) -> bool:
    """Check if a name is valid for use as a directory name on Windows."""
    if not name or not name.strip():
        return False
    if name.startswith('.'):
        return False
    if name in ('..', '.'):
        return False
    # Check Windows reserved names (case-insensitive)
    if name.upper() in WINDOWS_RESERVED_NAMES:
        return False
    return True


# **Feature: prompt-system-refactor, Property 9: Environment context freshness**
@settings(max_examples=100)
@given(subdir_name=st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-'),
    min_size=1,
    max_size=20
).filter(is_valid_dirname))
def test_environment_context_freshness(subdir_name: str):
    """
    Property 9: Environment context freshness
    
    For any change to the current working directory, the next call to
    build_environment SHALL return a context dict where the "cwd" value
    matches the new working directory.
    
    **Validates: Requirements 5.4**
    """
    builder = ContextBuilder()
    original_cwd = os.getcwd()
    tmpdir = None
    
    try:
        # Create a temporary directory with a subdirectory
        tmpdir = tempfile.mkdtemp()
        # Create subdirectory with the generated name
        subdir = Path(tmpdir) / subdir_name
        subdir.mkdir(parents=True, exist_ok=True)
        
        # Get initial environment
        env_before = builder.build_environment()
        
        # Change to the new directory
        os.chdir(str(subdir))
        
        # Get environment after change
        env_after = builder.build_environment()
        
        # The cwd should reflect the new directory
        assert env_after["cwd"] == str(subdir), (
            f"Expected cwd to be '{subdir}', got '{env_after['cwd']}'"
        )
        
        # The cwd should be different from before (unless we happened to be there)
        if env_before["cwd"] != str(subdir):
            assert env_after["cwd"] != env_before["cwd"], (
                "Environment should reflect directory change"
            )
    finally:
        # Always restore original directory BEFORE cleanup
        os.chdir(original_cwd)
        # Now we can safely clean up the temp directory
        if tmpdir and Path(tmpdir).exists():
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


# **Feature: prompt-system-refactor, Property 6: Variable interpolation completeness**
@settings(max_examples=100)
@given(
    var_names=st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_'),
            min_size=1,
            max_size=15
        ).filter(lambda x: x.isidentifier()),
        min_size=1,
        max_size=10,
        unique=True
    ),
    var_values=st.lists(
        st.text(min_size=0, max_size=50),
        min_size=1,
        max_size=10
    )
)
def test_variable_interpolation_completeness(var_names: list[str], var_values: list[str]):
    """
    Property 6: Variable interpolation completeness
    
    For any template string containing {{key}} placeholders and a variable
    dictionary, rendering SHALL replace every placeholder whose key exists
    in the dictionary with the corresponding value, leaving no {{key}}
    patterns for keys that were provided.
    
    **Validates: Requirements 7.1**
    """
    # Ensure we have matching lengths
    assume(len(var_names) > 0)
    
    # Pad var_values to match var_names length if needed
    while len(var_values) < len(var_names):
        var_values.append("")
    var_values = var_values[:len(var_names)]
    
    # Build variables dict
    variables = dict(zip(var_names, var_values))
    
    # Build a template with all variables
    template_parts = []
    for name in var_names:
        template_parts.append(f"{{{{" + name + "}}}}")
    template = " ".join(template_parts)
    
    # Interpolate
    result = interpolate(template, variables)
    
    # Verify no {{key}} patterns remain for provided keys
    for name in var_names:
        placeholder = "{{" + name + "}}"
        assert placeholder not in result, (
            f"Placeholder '{placeholder}' should have been replaced"
        )
    
    # Verify all values appear in the result
    for value in var_values:
        if value:  # Non-empty values should appear
            assert value in result, (
                f"Value '{value}' should appear in result"
            )


# Additional test for required variables
@settings(max_examples=100)
@given(
    var_name=st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_'),
        min_size=1,
        max_size=15
    ).filter(lambda x: x.isidentifier())
)
def test_required_variable_raises_error(var_name: str):
    """
    Test that missing required variables raise VariableError.
    
    **Validates: Requirements 7.2**
    """
    template = f"{{{{{var_name}}}}}"  # {{var_name}}
    
    # Should raise VariableError when required variable is missing
    with pytest.raises(VariableError) as exc_info:
        interpolate(template, {}, required_vars={var_name})
    
    assert var_name in str(exc_info.value)


# Test for optional variables (default behavior)
@settings(max_examples=100)
@given(
    var_name=st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_'),
        min_size=1,
        max_size=15
    ).filter(lambda x: x.isidentifier())
)
def test_optional_variable_replaced_with_empty(var_name: str):
    """
    Test that missing optional variables are replaced with empty string.
    
    **Validates: Requirements 7.3**
    """
    template = f"prefix_{{{{{var_name}}}}}_suffix"  # prefix_{{var_name}}_suffix
    
    # Should replace with empty string when variable is missing and not required
    result = interpolate(template, {})
    
    assert result == "prefix__suffix", (
        f"Expected 'prefix__suffix', got '{result}'"
    )
    assert f"{{{{{var_name}}}}}" not in result
