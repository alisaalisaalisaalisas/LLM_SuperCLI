"""
Tool parser module with plugin architecture.

Provides a modular tool parsing system that supports multiple syntax formats
through a plugin architecture. Parsers are tried in priority order until
one succeeds.

**Feature: qwen-tool-context-fix**
"""

import ast
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedToolCall:
    """A tool call parsed from model output.
    
    Attributes:
        name: Tool name (e.g., "read_file")
        arguments: Parsed arguments as a dictionary
        raw_text: Original matched text from the model output
        parser_name: Which parser found this tool call
    """
    name: str
    arguments: dict[str, Any]
    raw_text: str
    parser_name: str


class FormatParser(ABC):
    """Abstract base class for syntax format parsers.
    
    Each format parser handles a specific syntax format (e.g., Python-style,
    XML-style, JSON-style). Parsers are registered with ToolParser and tried
    in priority order.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Parser identifier (e.g., 'python', 'xml', 'json')."""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Priority order (lower = tried first).
        
        Suggested priority ranges:
        - 1-10: High priority (most common formats)
        - 11-50: Medium priority
        - 51-100: Low priority (fallback formats)
        """
        pass
    
    @abstractmethod
    def parse(self, content: str) -> list[ParsedToolCall]:
        """Parse tool calls from content.
        
        Args:
            content: The model output text to parse.
            
        Returns:
            List of ParsedToolCall objects found in the content.
            Returns empty list if no tool calls are found.
            
        Note:
            Implementations should NOT raise exceptions for malformed input.
            Instead, return an empty list or skip malformed calls.
        """
        pass


class ToolParser:
    """Parses tool calls from model output using registered format parsers.
    
    The ToolParser maintains a collection of FormatParser instances and
    tries them in priority order when parsing content. This allows for
    extensible support of multiple syntax formats.
    
    Example:
        parser = ToolParser()
        parser.register(PythonStyleParser())
        parser.register(XMLStyleParser())
        
        calls = parser.parse(model_output)
        for call in calls:
            print(f"Tool: {call.name}, Args: {call.arguments}")
    """
    
    def __init__(self) -> None:
        """Initialize the ToolParser with an empty parser list."""
        self._parsers: list[FormatParser] = []
    
    def register(self, parser: FormatParser) -> None:
        """Register a format parser.
        
        Parsers are automatically sorted by priority after registration.
        
        Args:
            parser: The FormatParser instance to register.
        """
        self._parsers.append(parser)
        # Sort by priority (lower = first)
        self._parsers.sort(key=lambda p: p.priority)
    
    def parse(self, content: str) -> list[ParsedToolCall]:
        """Parse tool calls trying each parser in priority order.
        
        Tries each registered parser in priority order. Returns results
        from the first parser that finds any tool calls. If no parser
        finds any calls, returns an empty list.
        
        Args:
            content: The model output text to parse.
            
        Returns:
            List of ParsedToolCall objects found by the highest-priority
            parser that succeeded. Returns empty list if no tool calls
            are found by any parser.
            
        Note:
            This method never raises exceptions. Malformed content or
            parser errors result in an empty list being returned.
        """
        if not content:
            return []
        
        for parser in self._parsers:
            try:
                calls = parser.parse(content)
                if calls:
                    return calls
            except Exception:
                # Parser failed, try next one
                continue
        
        return []
    
    @property
    def parsers(self) -> list[FormatParser]:
        """Get the list of registered parsers (sorted by priority)."""
        return list(self._parsers)


class PythonStyleParser(FormatParser):
    """Parses Python-style function calls from model output.
    
    Supports patterns like:
    - tool_name('arg')
    - tool_name("arg1", "arg2")
    - tool_name(param='value')
    - tool_name(param1='value1', param2='value2')
    - tool_name('positional', named='value')
    
    Handles string escaping and multi-line content within strings.
    Only matches known tool names to avoid false positives.
    
    **Feature: qwen-tool-context-fix**
    """
    
    # Known valid tool names - ONLY these will be parsed as tool calls
    _VALID_TOOLS = frozenset({
        'read_file', 'write_file', 'list_directory', 'create_directory',
        'run_command', 'get_current_directory',
    })
    
    # Pattern to match function calls for known tools only
    # This captures the function name and the arguments portion
    _FUNC_CALL_PATTERN = re.compile(
        r'\b(read_file|write_file|list_directory|create_directory|run_command|get_current_directory)\s*\(\s*'
        r'((?:[^()]*|\([^()]*\))*)'  # arguments (handles one level of nested parens)
        r'\s*\)',
        re.DOTALL
    )
    
    @property
    def name(self) -> str:
        return "python"
    
    @property
    def priority(self) -> int:
        return 10  # Highest priority
    
    def parse(self, content: str) -> list[ParsedToolCall]:
        """Parse Python-style tool calls from content.
        
        Only matches known tool names to avoid false positives like
        parsing "Frost" or "Shakespeare" as tool calls.
        
        Args:
            content: The model output text to parse.
            
        Returns:
            List of ParsedToolCall objects found in the content.
        """
        if not content:
            return []
        
        results: list[ParsedToolCall] = []
        
        for match in self._FUNC_CALL_PATTERN.finditer(content):
            func_name = match.group(1)
            args_str = match.group(2).strip()
            raw_text = match.group(0)
            
            # Double-check it's a valid tool (pattern should already ensure this)
            if func_name not in self._VALID_TOOLS:
                continue
            
            # Skip if it looks like a method call on an object (preceded by .)
            start_pos = match.start()
            if start_pos > 0 and content[start_pos - 1] == '.':
                continue
            
            # Try to parse the arguments
            try:
                arguments = self._parse_arguments(args_str)
                results.append(ParsedToolCall(
                    name=func_name,
                    arguments=arguments,
                    raw_text=raw_text,
                    parser_name=self.name,
                ))
            except Exception:
                # Skip malformed calls
                continue
        
        return results
    
    def _parse_arguments(self, args_str: str) -> dict[str, Any]:
        """Parse function arguments into a dictionary.
        
        Handles both positional and keyword arguments.
        Positional arguments are stored with keys 'arg0', 'arg1', etc.
        
        Args:
            args_str: The arguments portion of the function call.
            
        Returns:
            Dictionary of argument names to values.
        """
        if not args_str.strip():
            return {}
        
        arguments: dict[str, Any] = {}
        
        # Try to parse as a Python expression using AST
        # Wrap in a function call to make it valid Python
        try:
            # Create a fake function call to parse
            fake_call = f"_func({args_str})"
            tree = ast.parse(fake_call, mode='eval')
            
            if isinstance(tree.body, ast.Call):
                call = tree.body
                
                # Process positional arguments
                for i, arg in enumerate(call.args):
                    value = self._eval_ast_node(arg)
                    arguments[f'arg{i}'] = value
                
                # Process keyword arguments
                for kw in call.keywords:
                    if kw.arg is not None:
                        value = self._eval_ast_node(kw.value)
                        arguments[kw.arg] = value
                
        except SyntaxError:
            # Fall back to simple string parsing for single-argument cases
            arguments = self._fallback_parse(args_str)
        
        return arguments
    
    def _eval_ast_node(self, node: ast.AST) -> Any:
        """Safely evaluate an AST node to get its value.
        
        Only handles literals and simple expressions.
        
        Args:
            node: The AST node to evaluate.
            
        Returns:
            The Python value represented by the node.
        """
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Str):  # Python 3.7 compatibility
            return node.s
        elif isinstance(node, ast.Num):  # Python 3.7 compatibility
            return node.n
        elif isinstance(node, ast.List):
            return [self._eval_ast_node(elt) for elt in node.elts]
        elif isinstance(node, ast.Dict):
            keys = [self._eval_ast_node(k) if k is not None else None for k in node.keys]
            values = [self._eval_ast_node(v) for v in node.values]
            return dict(zip(keys, values))
        elif isinstance(node, ast.Tuple):
            return tuple(self._eval_ast_node(elt) for elt in node.elts)
        elif isinstance(node, ast.Set):
            return {self._eval_ast_node(elt) for elt in node.elts}
        elif isinstance(node, ast.NameConstant):  # Python 3.7 compatibility
            return node.value
        elif isinstance(node, ast.Name):
            # Handle True, False, None as names
            if node.id == 'True':
                return True
            elif node.id == 'False':
                return False
            elif node.id == 'None':
                return None
            else:
                # Return the name as a string (could be a variable reference)
                return node.id
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -self._eval_ast_node(node.operand)
            elif isinstance(node.op, ast.UAdd):
                return +self._eval_ast_node(node.operand)
        elif isinstance(node, ast.BinOp):
            # Handle simple binary operations for string concatenation
            if isinstance(node.op, ast.Add):
                left = self._eval_ast_node(node.left)
                right = self._eval_ast_node(node.right)
                if isinstance(left, str) and isinstance(right, str):
                    return left + right
        
        # For complex expressions, return a string representation
        return ast.dump(node)
    
    def _fallback_parse(self, args_str: str) -> dict[str, Any]:
        """Fallback parsing for simple cases when AST parsing fails.
        
        Args:
            args_str: The arguments string to parse.
            
        Returns:
            Dictionary with parsed arguments.
        """
        arguments: dict[str, Any] = {}
        
        # Try to extract quoted strings
        string_pattern = re.compile(r'''(['"])((?:\\.|(?!\1)[^\\])*)\1''')
        matches = list(string_pattern.finditer(args_str))
        
        if matches:
            for i, match in enumerate(matches):
                # Unescape the string
                value = match.group(2)
                value = value.replace('\\n', '\n')
                value = value.replace('\\t', '\t')
                value = value.replace('\\r', '\r')
                value = value.replace("\\'", "'")
                value = value.replace('\\"', '"')
                value = value.replace('\\\\', '\\')
                arguments[f'arg{i}'] = value
        
        return arguments


class XMLStyleParser(FormatParser):
    """Parses XML-style function calls from model output.
    
    Supports patterns like:
    - <function_calls><invoke name="tool"><parameter name="p">value</parameter></invoke></function_calls>
    - <tool_call><name>tool</name><arguments><arg>value</arg></arguments></tool_call>
    - <invoke name="tool"><parameter name="param">value</parameter></invoke>
    - <tool_name><param>value</param></tool_name> (direct tool name as tag)
    
    Handles nested XML and CDATA content.
    
    **Feature: qwen-tool-context-fix**
    """
    
    # Known valid tool names for direct tag format
    _VALID_TOOLS = frozenset({
        'read_file', 'write_file', 'list_directory', 'create_directory',
        'run_command', 'get_current_directory',
    })
    
    # Pattern to find function_calls blocks
    _FUNCTION_CALLS_PATTERN = re.compile(
        r'<function_calls>\s*(.*?)\s*</function_calls>',
        re.DOTALL | re.IGNORECASE
    )
    
    # Pattern to find invoke elements
    _INVOKE_PATTERN = re.compile(
        r'<invoke\s+name\s*=\s*["\']([^"\']+)["\']\s*>(.*?)</invoke>',
        re.DOTALL | re.IGNORECASE
    )
    
    # Pattern to find parameter elements
    _PARAMETER_PATTERN = re.compile(
        r'<parameter\s+name\s*=\s*["\']([^"\']+)["\']\s*>(.*?)</parameter>',
        re.DOTALL | re.IGNORECASE
    )
    
    # Pattern for standalone invoke (without function_calls wrapper)
    _STANDALONE_INVOKE_PATTERN = re.compile(
        r'<invoke\s+name\s*=\s*["\']([^"\']+)["\']\s*>(.*?)</invoke>',
        re.DOTALL | re.IGNORECASE
    )
    
    # Pattern for direct tool name as XML tag: <tool_name>...</tool_name>
    _DIRECT_TOOL_PATTERN = re.compile(
        r'<(read_file|write_file|list_directory|create_directory|run_command|get_current_directory)>\s*(.*?)\s*</\1>',
        re.DOTALL | re.IGNORECASE
    )
    
    @property
    def name(self) -> str:
        return "xml"
    
    @property
    def priority(self) -> int:
        return 20  # Second priority (after Python-style)
    
    def parse(self, content: str) -> list[ParsedToolCall]:
        """Parse XML-style tool calls from content.
        
        Args:
            content: The model output text to parse.
            
        Returns:
            List of ParsedToolCall objects found in the content.
        """
        if not content:
            return []
        
        results: list[ParsedToolCall] = []
        
        # First, try to find function_calls blocks
        function_calls_matches = self._FUNCTION_CALLS_PATTERN.findall(content)
        
        if function_calls_matches:
            for block in function_calls_matches:
                # Find all invoke elements within the block
                invoke_matches = self._INVOKE_PATTERN.findall(block)
                for tool_name, params_content in invoke_matches:
                    arguments = self._parse_parameters(params_content)
                    # Reconstruct raw text for this invoke
                    raw_text = f"<invoke name=\"{tool_name}\">{params_content}</invoke>"
                    results.append(ParsedToolCall(
                        name=tool_name,
                        arguments=arguments,
                        raw_text=raw_text,
                        parser_name=self.name,
                    ))
        
        # If no function_calls blocks found, try standalone invoke elements
        if not results:
            invoke_matches = self._STANDALONE_INVOKE_PATTERN.findall(content)
            for tool_name, params_content in invoke_matches:
                arguments = self._parse_parameters(params_content)
                raw_text = f"<invoke name=\"{tool_name}\">{params_content}</invoke>"
                results.append(ParsedToolCall(
                    name=tool_name,
                    arguments=arguments,
                    raw_text=raw_text,
                    parser_name=self.name,
                ))
        
        # If still no results, try direct tool name as XML tag format
        # e.g., <list_directory><path>.</path></list_directory>
        if not results:
            direct_matches = self._DIRECT_TOOL_PATTERN.findall(content)
            for tool_name, params_content in direct_matches:
                arguments = self._parse_direct_params(params_content)
                raw_text = f"<{tool_name}>{params_content}</{tool_name}>"
                results.append(ParsedToolCall(
                    name=tool_name,
                    arguments=arguments,
                    raw_text=raw_text,
                    parser_name=self.name,
                ))
        
        return results
    
    def _parse_parameters(self, params_content: str) -> dict[str, Any]:
        """Parse parameter elements from invoke content.
        
        Args:
            params_content: The content inside an invoke element.
            
        Returns:
            Dictionary of parameter names to values.
        """
        arguments: dict[str, Any] = {}
        
        # Find all parameter elements
        param_matches = self._PARAMETER_PATTERN.findall(params_content)
        
        for param_name, param_value in param_matches:
            # Handle CDATA content
            value = self._extract_cdata_or_text(param_value)
            arguments[param_name] = value
        
        return arguments
    
    def _parse_direct_params(self, params_content: str) -> dict[str, Any]:
        """Parse parameters from direct tool tag format.
        
        Handles format like: <path>.</path><content>text</content>
        
        Args:
            params_content: The content inside a direct tool tag.
            
        Returns:
            Dictionary of parameter names to values.
        """
        arguments: dict[str, Any] = {}
        
        # Pattern to match any XML tag as a parameter: <name>value</name>
        direct_param_pattern = re.compile(
            r'<(\w+)>(.*?)</\1>',
            re.DOTALL
        )
        
        param_matches = direct_param_pattern.findall(params_content)
        
        for param_name, param_value in param_matches:
            # Handle CDATA content
            value = self._extract_cdata_or_text(param_value)
            arguments[param_name] = value
        
        return arguments
    
    def _extract_cdata_or_text(self, content: str) -> str:
        """Extract text from content, handling CDATA sections.
        
        Args:
            content: The content that may contain CDATA.
            
        Returns:
            The extracted text value.
        """
        # Check for CDATA section first (before any stripping)
        cdata_pattern = re.compile(r'<!\[CDATA\[(.*?)\]\]>', re.DOTALL)
        cdata_match = cdata_pattern.search(content)
        
        if cdata_match:
            return cdata_match.group(1)
        
        # For plain text, strip outer whitespace but preserve internal content
        # This handles formatting whitespace around the value in XML
        stripped = content.strip()
        
        # Return plain text, unescaping XML entities
        return self._unescape_xml(stripped)
    
    def _unescape_xml(self, text: str) -> str:
        """Unescape XML entities in text.
        
        Args:
            text: Text with potential XML entities.
            
        Returns:
            Text with entities unescaped.
        """
        replacements = [
            ('&lt;', '<'),
            ('&gt;', '>'),
            ('&amp;', '&'),
            ('&quot;', '"'),
            ('&apos;', "'"),
        ]
        result = text
        for entity, char in replacements:
            result = result.replace(entity, char)
        return result
