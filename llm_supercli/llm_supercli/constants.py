"""
Constants and configuration defaults for llm_supercli.
"""
from pathlib import Path
from typing import Final

APP_NAME: Final[str] = "llm_supercli"
APP_VERSION: Final[str] = "1.0.0"
APP_DESCRIPTION: Final[str] = "A powerful multi-provider LLM command line interface"

CONFIG_DIR: Final[Path] = Path.home() / ".llm_supercli"
CONFIG_FILE: Final[Path] = CONFIG_DIR / "config.json"
HISTORY_DB: Final[Path] = CONFIG_DIR / "history.db"
SESSIONS_DIR: Final[Path] = CONFIG_DIR / "sessions"
THEMES_DIR: Final[Path] = CONFIG_DIR / "themes"
MCP_CONFIG_FILE: Final[Path] = CONFIG_DIR / "mcp_servers.json"
AUTH_CACHE_FILE: Final[Path] = CONFIG_DIR / ".auth_cache"

DEFAULT_THEME: Final[str] = "default"
DEFAULT_PROVIDER: Final[str] = "groq"
DEFAULT_MODEL: Final[str] = "llama-3.3-70b-versatile"

SLASH_PREFIX: Final[str] = "/"
SHELL_PREFIX: Final[str] = "!"
FILE_PREFIX: Final[str] = "@"

MAX_HISTORY_MESSAGES: Final[int] = 100
MAX_CONTEXT_LENGTH: Final[int] = 128000
DEFAULT_MAX_TOKENS: Final[int] = 4096
DEFAULT_TEMPERATURE: Final[float] = 0.7

# OAuth credentials - load from environment variables or config file
# DO NOT hardcode real credentials here - they will be exposed in git history
GOOGLE_CLIENT_ID: Final[str] = ""  # Set via GOOGLE_CLIENT_ID env var or config.json
GOOGLE_CLIENT_SECRET: Final[str] = ""  # Set via GOOGLE_CLIENT_SECRET env var or config.json
GITHUB_CLIENT_ID: Final[str] = ""  # Set via GITHUB_CLIENT_ID env var or config.json
GITHUB_CLIENT_SECRET: Final[str] = ""  # Set via GITHUB_CLIENT_SECRET env var or config.json

OAUTH_REDIRECT_PORT: Final[int] = 8765
OAUTH_TIMEOUT_SECONDS: Final[int] = 300

PROVIDERS: Final[dict] = {
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "models": [
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "google/gemini-pro-1.5",
            "meta-llama/llama-3.1-405b-instruct",
        ],
    },
    "together": {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "env_key": "TOGETHER_API_KEY",
        "models": [
            "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
            "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            "mistralai/Mixtral-8x22B-Instruct-v0.1",
        ],
    },
    "huggingface": {
        "name": "HuggingFace",
        "base_url": "https://api-inference.huggingface.co/models",
        "env_key": "HF_API_KEY",
        "models": [
            "meta-llama/Meta-Llama-3-70B-Instruct",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "google/gemma-7b-it",
        ],
    },
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434/api",
        "env_key": None,
        "models": [
            "llama3.2",
            "mistral",
            "codellama",
            "phi3",
        ],
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com",
        "env_key": "GEMINI_API_KEY",
        "models": [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
        ],
    },
    "qwen": {
        "name": "Qwen (Alibaba Cloud)",
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "env_key": None,
        "models": [
            "qwen-max",
            "qwen-plus",
            "qwen-turbo",
            "qwen2.5-72b-instruct",
            "qwen2.5-32b-instruct",
            "qwen2.5-14b-instruct",
            "qwen2.5-7b-instruct",
            "qwen2.5-coder-32b-instruct",
            "qwen2.5-math-72b-instruct",
            "qwq-32b-preview",
        ],
    },
}

SYSTEM_PROMPT: Final[str] = """You are a helpful AI assistant running in a command-line interface.
You provide concise, accurate responses. When asked about code, provide clean examples.
You can help with programming, writing, analysis, and general questions."""

HELP_TEXT: Final[str] = """
Available Commands:
  /help          - Show this help message
  /account       - View account information
  /login         - Login with Google or GitHub
  /logout        - Logout from current session
  /sessions      - List and manage chat sessions
  /new           - Start a new chat session
  /clear         - Clear the current screen
  /model         - Switch LLM model or provider
  /mcp           - Manage MCP server connections
  /settings      - View/edit settings
  /status        - Show current status
  /cost          - Show token usage and costs
  /favorite      - Save current session as favorite
  /compress      - Compress conversation context
  /rewind        - Rewind to previous message
  /quit          - Exit the CLI

Special Syntax:
  !command       - Execute shell command
  @file          - Include file contents in prompt
"""
