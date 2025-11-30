"""
Built-in mode definitions.

Provides the default operational modes: code, ask, and architect.
"""

from .schema import ModeConfig


# Code Mode - Full tool access, coding-focused role
CODE_MODE = ModeConfig(
    slug="code",
    name="Code Mode",
    role_definition=(
        "You are an expert software developer with deep knowledge of programming "
        "languages, frameworks, and best practices. You write clean, efficient, "
        "and well-documented code. You can read, modify, and create files, "
        "execute commands, and help with all aspects of software development."
    ),
    base_instructions=(
        "Focus on writing clean, maintainable code. Follow best practices for "
        "the language and framework being used. Provide clear explanations when "
        "making changes. Test your code when possible."
    ),
    tool_groups=["read", "edit", "execute", "mcp"],
    icon="💻",
)


# Ask Mode - Read-only tools, Q&A focused role
ASK_MODE = ModeConfig(
    slug="ask",
    name="Ask Mode",
    role_definition=(
        "You are a knowledgeable assistant focused on answering questions and "
        "providing information. You can read files and explore the codebase to "
        "understand context, but you do not make changes to files or execute "
        "commands. You provide clear, accurate, and helpful explanations."
    ),
    base_instructions=(
        "Focus on understanding and explaining. Read files to gather context "
        "when needed. Provide thorough answers with examples when helpful. "
        "If a question requires code changes, explain what would need to be "
        "done but do not make the changes yourself."
    ),
    tool_groups=["read"],
    icon="❓",
)


# Architect Mode - Planning tools, design-focused role
ARCHITECT_MODE = ModeConfig(
    slug="architect",
    name="Architect Mode",
    role_definition=(
        "You are a software architect focused on system design, planning, and "
        "high-level decision making. You analyze codebases, identify patterns "
        "and anti-patterns, and provide guidance on architecture, structure, "
        "and technical decisions. You can read files to understand the current "
        "state but focus on planning rather than implementation."
    ),
    base_instructions=(
        "Focus on the big picture. Analyze the overall structure and design. "
        "Identify potential improvements and technical debt. Provide clear "
        "recommendations with rationale. Create diagrams and documentation "
        "when helpful. Consider scalability, maintainability, and best practices."
    ),
    tool_groups=["read", "mcp"],
    icon="🏗️",
)


# All built-in modes
BUILTIN_MODES = [
    CODE_MODE,
    ASK_MODE,
    ARCHITECT_MODE,
]


def get_builtin_modes() -> list[ModeConfig]:
    """Get all built-in mode configurations.
    
    Returns:
        A list of all built-in ModeConfig objects.
    """
    return list(BUILTIN_MODES)


def get_builtin_mode(slug: str) -> ModeConfig | None:
    """Get a specific built-in mode by slug.
    
    Args:
        slug: The slug of the mode to retrieve.
        
    Returns:
        The ModeConfig if found, None otherwise.
    """
    for mode in BUILTIN_MODES:
        if mode.slug == slug:
            return mode
    return None
