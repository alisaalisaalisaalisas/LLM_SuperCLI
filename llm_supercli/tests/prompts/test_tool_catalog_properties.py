"""
Property-based tests for tool catalog.

Tests correctness properties defined in the design document using hypothesis.
"""

import pytest
from hypothesis import given, settings, strategies as st, assume

from llm_supercli.prompts.tools import ToolCatalog, ToolDefinition
from llm_supercli.prompts.modes import ModeConfig, VALID_TOOL_GROUPS


# Strategies for generating test data

def valid_tool_group_strategy():
    """Generate valid tool groups."""
    return st.sampled_from(list(VALID_TOOL_GROUPS))


@st.composite
def tool_definition_strategy(draw):
    """Generate a random ToolDefinition."""
    name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_'),
        min_size=1,
        max_size=30
    ))
    description = draw(st.text(min_size=1, max_size=100))
    group = draw(valid_tool_group_strategy())
    enabled = draw(st.booleans())
    
    return ToolDefinition(
        name=name,
        description=description,
        parameters={},
        group=group,
        enabled=enabled,
    )


@st.composite
def tool_list_strategy(draw, min_size=0, max_size=20):
    """Generate a list of tools with unique names."""
    count = draw(st.integers(min_value=min_size, max_value=max_size))
    tools = []
    used_names = set()
    
    for i in range(count):
        base_name = draw(st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_'),
            min_size=1,
            max_size=20
        ))
        # Ensure unique names
        name = f"{base_name}_{i}"
        if name in used_names:
            name = f"{name}_{len(used_names)}"
        used_names.add(name)
        
        description = draw(st.text(min_size=1, max_size=100))
        group = draw(valid_tool_group_strategy())
        enabled = draw(st.booleans())
        
        tools.append(ToolDefinition(
            name=name,
            description=description,
            parameters={},
            group=group,
            enabled=enabled,
        ))
    
    return tools


@st.composite
def mode_config_strategy(draw):
    """Generate a valid ModeConfig with random tool_groups."""
    slug = draw(st.from_regex(r"^[a-z][a-z0-9-]{0,10}$", fullmatch=True))
    name = draw(st.text(min_size=1, max_size=50))
    role_definition = draw(st.text(min_size=10, max_size=200))
    tool_groups = draw(st.lists(
        st.sampled_from(list(VALID_TOOL_GROUPS)),
        max_size=len(VALID_TOOL_GROUPS),
        unique=True,
    ))
    
    return ModeConfig(
        slug=slug,
        name=name,
        role_definition=role_definition,
        tool_groups=tool_groups,
    )


# **Feature: prompt-system-refactor, Property 3: Mode tool filtering correctness**
@settings(max_examples=100)
@given(
    tools=tool_list_strategy(min_size=1, max_size=20),
    mode=mode_config_strategy(),
)
def test_mode_tool_filtering_correctness(tools: list[ToolDefinition], mode: ModeConfig):
    """
    Property 3: Mode tool filtering correctness
    
    For any mode configuration with tool_groups and any list of tools with
    assigned groups, filtering SHALL produce a subset containing exactly
    those tools whose group is in the mode's tool_groups list.
    
    **Validates: Requirements 2.2, 4.1**
    """
    catalog = ToolCatalog(tools)
    filtered = catalog.filter_for_mode(mode)
    
    allowed_groups = set(mode.tool_groups)
    
    # All filtered tools should have their group in allowed_groups
    for tool in filtered:
        assert tool.group in allowed_groups, (
            f"Tool '{tool.name}' with group '{tool.group}' should not be in "
            f"filtered results. Allowed groups: {allowed_groups}"
        )
        # Filtered tools should be enabled
        assert tool.enabled, (
            f"Tool '{tool.name}' is disabled but appeared in filtered results"
        )
    
    # All enabled tools with allowed groups should be in filtered results
    expected_tools = [
        t for t in tools
        if t.group in allowed_groups and t.enabled
    ]
    
    filtered_names = {t.name for t in filtered}
    expected_names = {t.name for t in expected_tools}
    
    assert filtered_names == expected_names, (
        f"Filtered tools don't match expected. "
        f"Got: {filtered_names}, Expected: {expected_names}"
    )


# **Feature: prompt-system-refactor, Property 3: Mode tool filtering correctness**
@settings(max_examples=100)
@given(
    tools=tool_list_strategy(min_size=1, max_size=20),
    mode=mode_config_strategy(),
    tools_to_disable=st.integers(min_value=0, max_value=5),
)
def test_disabled_tools_excluded_from_filtering(
    tools: list[ToolDefinition],
    mode: ModeConfig,
    tools_to_disable: int,
):
    """
    Property 3: Mode tool filtering correctness (disabled tools)
    
    For any mode configuration and any list of tools where some tools
    are disabled via configuration, filtering SHALL exclude disabled tools
    even if their group is in the mode's tool_groups list.
    
    **Validates: Requirements 2.2, 4.1, 4.4**
    """
    assume(len(tools) > 0)
    
    catalog = ToolCatalog(tools)
    
    # Disable some tools
    disabled_names = set()
    for i, tool in enumerate(tools[:tools_to_disable]):
        catalog.disable_tool(tool.name)
        disabled_names.add(tool.name)
    
    filtered = catalog.filter_for_mode(mode)
    
    # No disabled tools should appear in filtered results
    for tool in filtered:
        assert tool.name not in disabled_names, (
            f"Disabled tool '{tool.name}' should not appear in filtered results"
        )


# **Feature: prompt-system-refactor, Property 3: Mode tool filtering correctness**
@settings(max_examples=100)
@given(
    tools=tool_list_strategy(min_size=1, max_size=20),
)
def test_empty_tool_groups_returns_empty(tools: list[ToolDefinition]):
    """
    Property 3: Mode tool filtering correctness (empty groups)
    
    For any mode configuration with empty tool_groups, filtering SHALL
    return an empty list regardless of available tools.
    
    **Validates: Requirements 2.2, 4.1**
    """
    mode = ModeConfig(
        slug="empty",
        name="Empty Mode",
        role_definition="A mode with no tool groups",
        tool_groups=[],
    )
    
    catalog = ToolCatalog(tools)
    filtered = catalog.filter_for_mode(mode)
    
    assert filtered == [], (
        f"Mode with empty tool_groups should return empty list, got {len(filtered)} tools"
    )



# Strategy for generating tool descriptions without XML-like patterns
# This is needed because we're testing protocol behavior, not whether
# user descriptions can contain arbitrary text
@st.composite
def safe_tool_list_strategy(draw, min_size=0, max_size=10):
    """Generate a list of tools with unique names and safe descriptions (no XML patterns)."""
    count = draw(st.integers(min_value=min_size, max_value=max_size))
    tools = []
    used_names = set()
    
    # Use alphanumeric descriptions to avoid XML-like patterns
    safe_alphabet = st.characters(whitelist_categories=('L', 'N', 'Zs'), whitelist_characters='_-.,!?')
    
    for i in range(count):
        base_name = draw(st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_'),
            min_size=1,
            max_size=20
        ))
        name = f"{base_name}_{i}"
        if name in used_names:
            name = f"{name}_{len(used_names)}"
        used_names.add(name)
        
        # Generate description without < or > characters
        description = draw(st.text(alphabet=safe_alphabet, min_size=1, max_size=100))
        group = draw(valid_tool_group_strategy())
        enabled = draw(st.booleans())
        
        tools.append(ToolDefinition(
            name=name,
            description=description,
            parameters={},
            group=group,
            enabled=enabled,
        ))
    
    return tools


# **Feature: prompt-system-refactor, Property 7: Protocol-appropriate tool syntax**
@settings(max_examples=100)
@given(
    tools=safe_tool_list_strategy(min_size=1, max_size=10),
)
def test_native_protocol_no_xml_syntax(tools: list[ToolDefinition]):
    """
    Property 7: Protocol-appropriate tool syntax (native protocol)
    
    For any prompt generation with protocol="native", the output SHALL NOT
    contain XML-style tool invocation examples.
    
    **Validates: Requirements 6.3, 6.4**
    """
    # Create a mode that allows all tool groups so we get some output
    mode = ModeConfig(
        slug="test",
        name="Test Mode",
        role_definition="A test mode for protocol testing",
        tool_groups=list(VALID_TOOL_GROUPS),
    )
    
    # Ensure at least one tool is enabled and has an allowed group
    enabled_tools = [t for t in tools if t.enabled]
    assume(len(enabled_tools) > 0)
    
    catalog = ToolCatalog(tools)
    output = catalog.render(mode, protocol="native")
    
    # If there's output, it should NOT contain XML-style syntax
    if output:
        # Check for XML-style tool invocation patterns
        xml_patterns = [
            "<function_calls>",
            "</function_calls>",
            "<invoke",
            "</invoke>",
            "<parameter",
            "</parameter>",
        ]
        
        for pattern in xml_patterns:
            assert pattern not in output, (
                f"Native protocol output should not contain XML pattern '{pattern}'. "
                f"Output: {output[:500]}..."
            )


# **Feature: prompt-system-refactor, Property 7: Protocol-appropriate tool syntax**
@settings(max_examples=100)
@given(
    tools=tool_list_strategy(min_size=1, max_size=10),
)
def test_text_protocol_has_xml_syntax(tools: list[ToolDefinition]):
    """
    Property 7: Protocol-appropriate tool syntax (text protocol)
    
    For any prompt generation with protocol="text", the output SHALL contain
    explicit function call syntax examples.
    
    **Validates: Requirements 6.3, 6.4**
    """
    # Create a mode that allows all tool groups so we get some output
    mode = ModeConfig(
        slug="test",
        name="Test Mode",
        role_definition="A test mode for protocol testing",
        tool_groups=list(VALID_TOOL_GROUPS),
    )
    
    # Ensure at least one tool is enabled and has an allowed group
    enabled_tools = [t for t in tools if t.enabled]
    assume(len(enabled_tools) > 0)
    
    catalog = ToolCatalog(tools)
    output = catalog.render(mode, protocol="text")
    
    # If there's output, it SHOULD contain XML-style syntax
    if output:
        # Check for XML-style tool invocation patterns
        assert "<function_calls>" in output, (
            f"Text protocol output should contain '<function_calls>'. "
            f"Output: {output[:500]}..."
        )
        assert "</function_calls>" in output, (
            f"Text protocol output should contain '</function_calls>'. "
            f"Output: {output[:500]}..."
        )
        assert "<invoke" in output, (
            f"Text protocol output should contain '<invoke'. "
            f"Output: {output[:500]}..."
        )


# **Feature: prompt-system-refactor, Property 7: Protocol-appropriate tool syntax**
@settings(max_examples=100)
@given(
    tools=tool_list_strategy(min_size=1, max_size=10),
    protocol=st.sampled_from(["text", "native"]),
)
def test_protocol_consistency(tools: list[ToolDefinition], protocol: str):
    """
    Property 7: Protocol-appropriate tool syntax (consistency)
    
    For any prompt generation, the protocol parameter should consistently
    determine whether XML syntax is included or excluded.
    
    **Validates: Requirements 6.3, 6.4**
    """
    mode = ModeConfig(
        slug="test",
        name="Test Mode",
        role_definition="A test mode for protocol testing",
        tool_groups=list(VALID_TOOL_GROUPS),
    )
    
    enabled_tools = [t for t in tools if t.enabled]
    assume(len(enabled_tools) > 0)
    
    catalog = ToolCatalog(tools)
    output = catalog.render(mode, protocol=protocol)
    
    if output:
        has_xml = "<function_calls>" in output
        
        if protocol == "native":
            assert not has_xml, "Native protocol should not have XML syntax"
        else:  # text
            assert has_xml, "Text protocol should have XML syntax"
