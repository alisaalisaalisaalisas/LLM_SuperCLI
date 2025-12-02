"""
Property-based tests for tool parser.

Tests correctness properties defined in the design document using hypothesis.

**Feature: qwen-tool-context-fix**
"""

import pytest
from hypothesis import given, settings, strategies as st, assume, HealthCheck

from llm_supercli.prompts.tools import ParsedToolCall, FormatParser, ToolParser, PythonStyleParser


# Test parser implementations for property testing

class MockParser(FormatParser):
    """A mock parser for testing that returns configurable results."""
    
    def __init__(self, parser_name: str, parser_priority: int, match_pattern: str = ""):
        self._name = parser_name
        self._priority = parser_priority
        self._match_pattern = match_pattern
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def priority(self) -> int:
        return self._priority
    
    def parse(self, content: str) -> list[ParsedToolCall]:
        """Return a tool call if match_pattern is found in content."""
        if self._match_pattern and self._match_pattern in content:
            return [ParsedToolCall(
                name=f"tool_from_{self._name}",
                arguments={},
                raw_text=content,
                parser_name=self._name,
            )]
        return []


class AlwaysMatchParser(FormatParser):
    """A parser that always returns a result for non-empty content."""
    
    def __init__(self, parser_name: str, parser_priority: int):
        self._name = parser_name
        self._priority = parser_priority
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def priority(self) -> int:
        return self._priority
    
    def parse(self, content: str) -> list[ParsedToolCall]:
        if content.strip():
            return [ParsedToolCall(
                name=f"tool_from_{self._name}",
                arguments={},
                raw_text=content,
                parser_name=self._name,
            )]
        return []


class NeverMatchParser(FormatParser):
    """A parser that never matches anything."""
    
    def __init__(self, parser_name: str, parser_priority: int):
        self._name = parser_name
        self._priority = parser_priority
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def priority(self) -> int:
        return self._priority
    
    def parse(self, content: str) -> list[ParsedToolCall]:
        return []


class ExceptionParser(FormatParser):
    """A parser that always raises an exception."""
    
    def __init__(self, parser_name: str, parser_priority: int):
        self._name = parser_name
        self._priority = parser_priority
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def priority(self) -> int:
        return self._priority
    
    def parse(self, content: str) -> list[ParsedToolCall]:
        raise ValueError("Parser error")


# Strategies for generating test data

@st.composite
def priority_list_strategy(draw, min_size=2, max_size=10):
    """Generate a list of unique priorities."""
    count = draw(st.integers(min_value=min_size, max_value=max_size))
    priorities = draw(st.lists(
        st.integers(min_value=1, max_value=100),
        min_size=count,
        max_size=count,
        unique=True,
    ))
    return priorities


@st.composite
def non_empty_content_strategy(draw):
    """Generate non-empty content strings."""
    content = draw(st.text(min_size=1, max_size=200))
    assume(content.strip())  # Ensure non-whitespace content
    return content


# **Feature: qwen-tool-context-fix, Property 3: Parser priority ordering**
# **Validates: Requirements 5.3**
@settings(max_examples=100)
@given(
    priorities=priority_list_strategy(min_size=2, max_size=5),
    content=non_empty_content_strategy(),
)
def test_parser_priority_ordering(priorities: list[int], content: str):
    """
    Property 3: Parser priority ordering
    
    For any content that matches multiple parser formats, the ToolParser
    SHALL return results from the highest-priority parser that succeeds.
    
    **Feature: qwen-tool-context-fix, Property 3: Parser priority ordering**
    **Validates: Requirements 5.3**
    """
    tool_parser = ToolParser()
    
    # Register parsers with different priorities - all will match
    for i, priority in enumerate(priorities):
        parser = AlwaysMatchParser(f"parser_{priority}", priority)
        tool_parser.register(parser)
    
    # Parse the content
    results = tool_parser.parse(content)
    
    # Should get results from the lowest priority (highest precedence) parser
    assert len(results) > 0, "Should have found tool calls"
    
    min_priority = min(priorities)
    expected_parser_name = f"parser_{min_priority}"
    
    assert results[0].parser_name == expected_parser_name, (
        f"Expected results from parser with priority {min_priority} "
        f"('{expected_parser_name}'), but got from '{results[0].parser_name}'. "
        f"Registered priorities: {sorted(priorities)}"
    )


# **Feature: qwen-tool-context-fix, Property 3: Parser priority ordering**
# **Validates: Requirements 5.3**
@settings(max_examples=100)
@given(
    priorities=priority_list_strategy(min_size=2, max_size=5),
)
def test_parsers_sorted_by_priority(priorities: list[int]):
    """
    Property 3: Parser priority ordering (registration order)
    
    For any set of parsers registered in any order, the ToolParser SHALL
    maintain them sorted by priority (lowest first).
    
    **Feature: qwen-tool-context-fix, Property 3: Parser priority ordering**
    **Validates: Requirements 5.3**
    """
    tool_parser = ToolParser()
    
    # Register parsers in the given order (which may not be sorted)
    for priority in priorities:
        parser = NeverMatchParser(f"parser_{priority}", priority)
        tool_parser.register(parser)
    
    # Check that parsers are sorted by priority
    registered_priorities = [p.priority for p in tool_parser.parsers]
    assert registered_priorities == sorted(priorities), (
        f"Parsers should be sorted by priority. "
        f"Got: {registered_priorities}, Expected: {sorted(priorities)}"
    )



# **Feature: qwen-tool-context-fix, Property 4: Graceful parsing failure**
# **Validates: Requirements 1.5, 5.4**
@settings(max_examples=100)
@given(
    content=st.text(max_size=500),
)
def test_graceful_parsing_failure_empty_result(content: str):
    """
    Property 4: Graceful parsing failure
    
    For any content that contains no valid tool calls or malformed syntax,
    the ToolParser SHALL return an empty list without raising exceptions.
    
    **Feature: qwen-tool-context-fix, Property 4: Graceful parsing failure**
    **Validates: Requirements 1.5, 5.4**
    """
    tool_parser = ToolParser()
    
    # Register parsers that never match
    tool_parser.register(NeverMatchParser("never1", 10))
    tool_parser.register(NeverMatchParser("never2", 20))
    
    # Should return empty list, not raise exception
    results = tool_parser.parse(content)
    
    assert isinstance(results, list), "Result should be a list"
    assert len(results) == 0, "Should return empty list when no parsers match"


# **Feature: qwen-tool-context-fix, Property 4: Graceful parsing failure**
# **Validates: Requirements 1.5, 5.4**
@settings(max_examples=100)
@given(
    content=st.text(max_size=500),
)
def test_graceful_parsing_failure_with_exceptions(content: str):
    """
    Property 4: Graceful parsing failure (exception handling)
    
    For any content, if a parser raises an exception, the ToolParser SHALL
    catch it and continue to the next parser without crashing.
    
    **Feature: qwen-tool-context-fix, Property 4: Graceful parsing failure**
    **Validates: Requirements 1.5, 5.4**
    """
    tool_parser = ToolParser()
    
    # Register an exception-throwing parser first
    tool_parser.register(ExceptionParser("exception", 5))
    # Then a parser that never matches
    tool_parser.register(NeverMatchParser("never", 10))
    
    # Should not raise exception, should return empty list
    results = tool_parser.parse(content)
    
    assert isinstance(results, list), "Result should be a list"
    assert len(results) == 0, "Should return empty list when parsers fail"


# **Feature: qwen-tool-context-fix, Property 4: Graceful parsing failure**
# **Validates: Requirements 1.5, 5.4**
@settings(max_examples=100)
@given(
    content=non_empty_content_strategy(),
)
def test_graceful_parsing_failure_fallback_to_working_parser(content: str):
    """
    Property 4: Graceful parsing failure (fallback behavior)
    
    For any content, if a higher-priority parser raises an exception,
    the ToolParser SHALL fall back to lower-priority parsers.
    
    **Feature: qwen-tool-context-fix, Property 4: Graceful parsing failure**
    **Validates: Requirements 1.5, 5.4**
    """
    tool_parser = ToolParser()
    
    # Register an exception-throwing parser with highest priority
    tool_parser.register(ExceptionParser("exception", 5))
    # Then a parser that always matches with lower priority
    tool_parser.register(AlwaysMatchParser("fallback", 10))
    
    # Should fall back to the working parser
    results = tool_parser.parse(content)
    
    assert isinstance(results, list), "Result should be a list"
    assert len(results) > 0, "Should have results from fallback parser"
    assert results[0].parser_name == "fallback", (
        f"Should get results from fallback parser, got '{results[0].parser_name}'"
    )


# **Feature: qwen-tool-context-fix, Property 4: Graceful parsing failure**
# **Validates: Requirements 1.5, 5.4**
def test_graceful_parsing_failure_empty_content():
    """
    Property 4: Graceful parsing failure (empty content)
    
    For empty content, the ToolParser SHALL return an empty list
    without calling any parsers.
    
    **Feature: qwen-tool-context-fix, Property 4: Graceful parsing failure**
    **Validates: Requirements 1.5, 5.4**
    """
    tool_parser = ToolParser()
    
    # Register parsers
    tool_parser.register(AlwaysMatchParser("always", 10))
    
    # Empty string should return empty list
    results = tool_parser.parse("")
    assert results == [], "Empty content should return empty list"
    
    # None-like empty should also work
    results = tool_parser.parse("")
    assert results == [], "Empty string should return empty list"


# **Feature: qwen-tool-context-fix, Property 4: Graceful parsing failure**
# **Validates: Requirements 1.5, 5.4**
def test_graceful_parsing_failure_no_parsers():
    """
    Property 4: Graceful parsing failure (no parsers registered)
    
    For any content with no parsers registered, the ToolParser SHALL
    return an empty list without raising exceptions.
    
    **Feature: qwen-tool-context-fix, Property 4: Graceful parsing failure**
    **Validates: Requirements 1.5, 5.4**
    """
    tool_parser = ToolParser()
    
    # No parsers registered
    results = tool_parser.parse("some content")
    
    assert isinstance(results, list), "Result should be a list"
    assert len(results) == 0, "Should return empty list with no parsers"


# =============================================================================
# Property 1: Python-style parsing correctness
# =============================================================================

# Strategies for generating valid Python-style tool calls

@st.composite
def valid_tool_name_strategy(draw):
    """Generate valid tool names that the PythonStyleParser actually supports.
    
    The PythonStyleParser only matches a specific set of known tool names
    to avoid false positives. This strategy generates from that set.
    """
    # Use the actual valid tool names from PythonStyleParser._VALID_TOOLS
    valid_tools = [
        'read_file', 'write_file', 'list_directory', 'create_directory',
        'run_command', 'get_current_directory',
    ]
    return draw(st.sampled_from(valid_tools))


@st.composite
def safe_string_value_strategy(draw):
    """Generate string values that are safe for Python parsing."""
    # Use printable ASCII characters, excluding quotes and backslashes for simplicity
    safe_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-./:'
    value = draw(st.text(alphabet=safe_chars, min_size=1, max_size=50))
    assume(value.strip())  # Ensure non-empty after strip
    return value


@st.composite
def python_style_single_arg_call_strategy(draw):
    """Generate a Python-style tool call with a single string argument."""
    tool_name = draw(valid_tool_name_strategy())
    arg_value = draw(safe_string_value_strategy())
    quote = draw(st.sampled_from(["'", '"']))
    
    call_str = f"{tool_name}({quote}{arg_value}{quote})"
    return {
        'call_str': call_str,
        'expected_name': tool_name,
        'expected_args': {'arg0': arg_value},
    }


@st.composite
def python_style_multi_arg_call_strategy(draw):
    """Generate a Python-style tool call with multiple string arguments."""
    tool_name = draw(valid_tool_name_strategy())
    num_args = draw(st.integers(min_value=2, max_value=4))
    
    args = []
    expected_args = {}
    for i in range(num_args):
        arg_value = draw(safe_string_value_strategy())
        quote = draw(st.sampled_from(["'", '"']))
        args.append(f"{quote}{arg_value}{quote}")
        expected_args[f'arg{i}'] = arg_value
    
    call_str = f"{tool_name}({', '.join(args)})"
    return {
        'call_str': call_str,
        'expected_name': tool_name,
        'expected_args': expected_args,
    }


import keyword

# Python reserved keywords that cannot be used as argument names
_PYTHON_KEYWORDS = frozenset(keyword.kwlist)


@st.composite
def valid_kwarg_name_strategy(draw):
    """Generate valid Python keyword argument names.
    
    Excludes Python reserved keywords (like 'as', 'if', 'for', etc.)
    since they cannot be used as keyword argument names in valid Python syntax.
    """
    first_char = draw(st.sampled_from('abcdefghijklmnopqrstuvwxyz'))
    rest_chars = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789_',
        min_size=1,
        max_size=10
    ))
    name = first_char + rest_chars
    # Exclude Python reserved keywords - they can't be used as kwarg names
    assume(name not in _PYTHON_KEYWORDS)
    return name


@st.composite
def python_style_kwarg_call_strategy(draw):
    """Generate a Python-style tool call with keyword arguments."""
    tool_name = draw(valid_tool_name_strategy())
    num_kwargs = draw(st.integers(min_value=1, max_value=3))
    
    kwargs = []
    expected_args = {}
    used_names = set()
    
    for _ in range(num_kwargs):
        kwarg_name = draw(valid_kwarg_name_strategy())
        # Ensure unique kwarg names
        while kwarg_name in used_names:
            kwarg_name = draw(valid_kwarg_name_strategy())
        used_names.add(kwarg_name)
        
        kwarg_value = draw(safe_string_value_strategy())
        quote = draw(st.sampled_from(["'", '"']))
        kwargs.append(f"{kwarg_name}={quote}{kwarg_value}{quote}")
        expected_args[kwarg_name] = kwarg_value
    
    call_str = f"{tool_name}({', '.join(kwargs)})"
    return {
        'call_str': call_str,
        'expected_name': tool_name,
        'expected_args': expected_args,
    }


# **Feature: qwen-tool-context-fix, Property 1: Python-style parsing correctness**
# **Validates: Requirements 1.2**
@settings(max_examples=100)
@given(call_data=python_style_single_arg_call_strategy())
def test_python_style_parsing_single_arg(call_data: dict):
    """
    Property 1: Python-style parsing correctness (single argument)
    
    For any valid Python-style tool call string with a single string argument,
    parsing SHALL extract the correct tool name and argument value.
    
    **Feature: qwen-tool-context-fix, Property 1: Python-style parsing correctness**
    **Validates: Requirements 1.2**
    """
    parser = PythonStyleParser()
    
    call_str = call_data['call_str']
    expected_name = call_data['expected_name']
    expected_args = call_data['expected_args']
    
    results = parser.parse(call_str)
    
    assert len(results) == 1, f"Expected 1 result, got {len(results)} for: {call_str}"
    
    result = results[0]
    assert result.name == expected_name, (
        f"Expected tool name '{expected_name}', got '{result.name}' for: {call_str}"
    )
    assert result.arguments == expected_args, (
        f"Expected args {expected_args}, got {result.arguments} for: {call_str}"
    )
    assert result.parser_name == "python", (
        f"Expected parser_name 'python', got '{result.parser_name}'"
    )


# **Feature: qwen-tool-context-fix, Property 1: Python-style parsing correctness**
# **Validates: Requirements 1.2**
@settings(max_examples=100)
@given(call_data=python_style_multi_arg_call_strategy())
def test_python_style_parsing_multi_arg(call_data: dict):
    """
    Property 1: Python-style parsing correctness (multiple arguments)
    
    For any valid Python-style tool call string with multiple string arguments,
    parsing SHALL extract the correct tool name and all argument values.
    
    **Feature: qwen-tool-context-fix, Property 1: Python-style parsing correctness**
    **Validates: Requirements 1.2**
    """
    parser = PythonStyleParser()
    
    call_str = call_data['call_str']
    expected_name = call_data['expected_name']
    expected_args = call_data['expected_args']
    
    results = parser.parse(call_str)
    
    assert len(results) == 1, f"Expected 1 result, got {len(results)} for: {call_str}"
    
    result = results[0]
    assert result.name == expected_name, (
        f"Expected tool name '{expected_name}', got '{result.name}' for: {call_str}"
    )
    assert result.arguments == expected_args, (
        f"Expected args {expected_args}, got {result.arguments} for: {call_str}"
    )


# **Feature: qwen-tool-context-fix, Property 1: Python-style parsing correctness**
# **Validates: Requirements 1.2**
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(call_data=python_style_kwarg_call_strategy())
def test_python_style_parsing_kwargs(call_data: dict):
    """
    Property 1: Python-style parsing correctness (keyword arguments)
    
    For any valid Python-style tool call string with keyword arguments,
    parsing SHALL extract the correct tool name and all keyword argument values.
    
    **Feature: qwen-tool-context-fix, Property 1: Python-style parsing correctness**
    **Validates: Requirements 1.2**
    """
    parser = PythonStyleParser()
    
    call_str = call_data['call_str']
    expected_name = call_data['expected_name']
    expected_args = call_data['expected_args']
    
    results = parser.parse(call_str)
    
    assert len(results) == 1, f"Expected 1 result, got {len(results)} for: {call_str}"
    
    result = results[0]
    assert result.name == expected_name, (
        f"Expected tool name '{expected_name}', got '{result.name}' for: {call_str}"
    )
    assert result.arguments == expected_args, (
        f"Expected args {expected_args}, got {result.arguments} for: {call_str}"
    )


# =============================================================================
# Property 2: XML-style parsing correctness
# =============================================================================

from llm_supercli.prompts.tools import XMLStyleParser


@st.composite
def xml_tool_name_strategy(draw):
    """Generate valid XML-compatible tool names."""
    # Start with letter or underscore, followed by letters, digits, underscores, hyphens
    first_char = draw(st.sampled_from('abcdefghijklmnopqrstuvwxyz_'))
    rest_chars = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789_',
        min_size=2,
        max_size=20
    ))
    return first_char + rest_chars


@st.composite
def xml_safe_param_name_strategy(draw):
    """Generate valid XML parameter names."""
    first_char = draw(st.sampled_from('abcdefghijklmnopqrstuvwxyz'))
    rest_chars = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789_',
        min_size=1,
        max_size=15
    ))
    return first_char + rest_chars


@st.composite
def xml_safe_param_value_strategy(draw):
    """Generate parameter values safe for XML (no special chars that need escaping).
    
    Values are trimmed since XML parsers typically strip whitespace around text content.
    """
    # Use safe characters that don't need XML escaping (no leading/trailing spaces)
    safe_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-./:'
    value = draw(st.text(alphabet=safe_chars, min_size=1, max_size=50))
    assume(value.strip())  # Ensure non-empty after strip
    return value.strip()  # Return trimmed value to match parser behavior


@st.composite
def xml_style_single_param_call_strategy(draw):
    """Generate an XML-style tool call with a single parameter."""
    tool_name = draw(xml_tool_name_strategy())
    param_name = draw(xml_safe_param_name_strategy())
    param_value = draw(xml_safe_param_value_strategy())
    
    # Format: <function_calls><invoke name="tool"><parameter name="p">value</parameter></invoke></function_calls>
    call_str = (
        f'<function_calls>'
        f'<invoke name="{tool_name}">'
        f'<parameter name="{param_name}">{param_value}</parameter>'
        f'</invoke>'
        f'</function_calls>'
    )
    
    return {
        'call_str': call_str,
        'expected_name': tool_name,
        'expected_args': {param_name: param_value},
    }


@st.composite
def xml_style_multi_param_call_strategy(draw):
    """Generate an XML-style tool call with multiple parameters."""
    tool_name = draw(xml_tool_name_strategy())
    # Use fixed number of params to avoid slow generation
    num_params = 2
    
    params_xml = []
    expected_args = {}
    
    # Use simple indexed param names to avoid uniqueness checks
    for i in range(num_params):
        param_name = f"param{i}"
        param_value = draw(xml_safe_param_value_strategy())
        params_xml.append(f'<parameter name="{param_name}">{param_value}</parameter>')
        expected_args[param_name] = param_value
    
    call_str = (
        f'<function_calls>'
        f'<invoke name="{tool_name}">'
        f'{"".join(params_xml)}'
        f'</invoke>'
        f'</function_calls>'
    )
    
    return {
        'call_str': call_str,
        'expected_name': tool_name,
        'expected_args': expected_args,
    }


@st.composite
def xml_style_standalone_invoke_strategy(draw):
    """Generate a standalone invoke element (without function_calls wrapper)."""
    tool_name = draw(xml_tool_name_strategy())
    param_name = draw(xml_safe_param_name_strategy())
    param_value = draw(xml_safe_param_value_strategy())
    
    # Format: <invoke name="tool"><parameter name="p">value</parameter></invoke>
    call_str = (
        f'<invoke name="{tool_name}">'
        f'<parameter name="{param_name}">{param_value}</parameter>'
        f'</invoke>'
    )
    
    return {
        'call_str': call_str,
        'expected_name': tool_name,
        'expected_args': {param_name: param_value},
    }


@st.composite
def xml_style_with_cdata_strategy(draw):
    """Generate an XML-style tool call with CDATA content."""
    tool_name = draw(xml_tool_name_strategy())
    param_name = draw(xml_safe_param_name_strategy())
    # For CDATA, we can use more characters since they're wrapped
    param_value = draw(xml_safe_param_value_strategy())
    
    call_str = (
        f'<function_calls>'
        f'<invoke name="{tool_name}">'
        f'<parameter name="{param_name}"><![CDATA[{param_value}]]></parameter>'
        f'</invoke>'
        f'</function_calls>'
    )
    
    return {
        'call_str': call_str,
        'expected_name': tool_name,
        'expected_args': {param_name: param_value},
    }


# **Feature: qwen-tool-context-fix, Property 2: XML-style parsing correctness**
# **Validates: Requirements 1.3**
@settings(max_examples=100)
@given(call_data=xml_style_single_param_call_strategy())
def test_xml_style_parsing_single_param(call_data: dict):
    """
    Property 2: XML-style parsing correctness (single parameter)
    
    For any valid XML-style tool call with a single parameter,
    parsing SHALL extract the correct tool name and parameter value.
    
    **Feature: qwen-tool-context-fix, Property 2: XML-style parsing correctness**
    **Validates: Requirements 1.3**
    """
    parser = XMLStyleParser()
    
    call_str = call_data['call_str']
    expected_name = call_data['expected_name']
    expected_args = call_data['expected_args']
    
    results = parser.parse(call_str)
    
    assert len(results) == 1, f"Expected 1 result, got {len(results)} for: {call_str}"
    
    result = results[0]
    assert result.name == expected_name, (
        f"Expected tool name '{expected_name}', got '{result.name}' for: {call_str}"
    )
    assert result.arguments == expected_args, (
        f"Expected args {expected_args}, got {result.arguments} for: {call_str}"
    )
    assert result.parser_name == "xml", (
        f"Expected parser_name 'xml', got '{result.parser_name}'"
    )


# **Feature: qwen-tool-context-fix, Property 2: XML-style parsing correctness**
# **Validates: Requirements 1.3**
from hypothesis import HealthCheck
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow])
@given(call_data=xml_style_multi_param_call_strategy())
def test_xml_style_parsing_multi_param(call_data: dict):
    """
    Property 2: XML-style parsing correctness (multiple parameters)
    
    For any valid XML-style tool call with multiple parameters,
    parsing SHALL extract the correct tool name and all parameter values.
    
    **Feature: qwen-tool-context-fix, Property 2: XML-style parsing correctness**
    **Validates: Requirements 1.3**
    """
    parser = XMLStyleParser()
    
    call_str = call_data['call_str']
    expected_name = call_data['expected_name']
    expected_args = call_data['expected_args']
    
    results = parser.parse(call_str)
    
    assert len(results) == 1, f"Expected 1 result, got {len(results)} for: {call_str}"
    
    result = results[0]
    assert result.name == expected_name, (
        f"Expected tool name '{expected_name}', got '{result.name}' for: {call_str}"
    )
    assert result.arguments == expected_args, (
        f"Expected args {expected_args}, got {result.arguments} for: {call_str}"
    )


# **Feature: qwen-tool-context-fix, Property 2: XML-style parsing correctness**
# **Validates: Requirements 1.3**
@settings(max_examples=100)
@given(call_data=xml_style_standalone_invoke_strategy())
def test_xml_style_parsing_standalone_invoke(call_data: dict):
    """
    Property 2: XML-style parsing correctness (standalone invoke)
    
    For any valid standalone invoke element (without function_calls wrapper),
    parsing SHALL extract the correct tool name and parameter values.
    
    **Feature: qwen-tool-context-fix, Property 2: XML-style parsing correctness**
    **Validates: Requirements 1.3**
    """
    parser = XMLStyleParser()
    
    call_str = call_data['call_str']
    expected_name = call_data['expected_name']
    expected_args = call_data['expected_args']
    
    results = parser.parse(call_str)
    
    assert len(results) == 1, f"Expected 1 result, got {len(results)} for: {call_str}"
    
    result = results[0]
    assert result.name == expected_name, (
        f"Expected tool name '{expected_name}', got '{result.name}' for: {call_str}"
    )
    assert result.arguments == expected_args, (
        f"Expected args {expected_args}, got {result.arguments} for: {call_str}"
    )


# **Feature: qwen-tool-context-fix, Property 2: XML-style parsing correctness**
# **Validates: Requirements 1.3**
@settings(max_examples=100)
@given(call_data=xml_style_with_cdata_strategy())
def test_xml_style_parsing_with_cdata(call_data: dict):
    """
    Property 2: XML-style parsing correctness (CDATA content)
    
    For any valid XML-style tool call with CDATA-wrapped parameter values,
    parsing SHALL extract the correct tool name and unwrapped parameter values.
    
    **Feature: qwen-tool-context-fix, Property 2: XML-style parsing correctness**
    **Validates: Requirements 1.3**
    """
    parser = XMLStyleParser()
    
    call_str = call_data['call_str']
    expected_name = call_data['expected_name']
    expected_args = call_data['expected_args']
    
    results = parser.parse(call_str)
    
    assert len(results) == 1, f"Expected 1 result, got {len(results)} for: {call_str}"
    
    result = results[0]
    assert result.name == expected_name, (
        f"Expected tool name '{expected_name}', got '{result.name}' for: {call_str}"
    )
    assert result.arguments == expected_args, (
        f"Expected args {expected_args}, got {result.arguments} for: {call_str}"
    )
