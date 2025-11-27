# LLM SuperCLI

A powerful multi-provider LLM command line interface with OAuth support, interactive menus, and streaming responses.

## Features

- **Multi-Provider Support**: Groq, OpenRouter, Together AI, HuggingFace, Ollama, Google Gemini, Qwen
- **OAuth Authentication**: Login with Google Gemini or Qwen using OAuth credentials
- **Interactive UI**: Rich terminal interface with autocomplete, syntax highlighting, and falling menus
- **Streaming Responses**: Real-time token streaming for all providers
- **Session Management**: Save, load, and manage conversation sessions
- **MCP Integration**: Model Context Protocol server connections
- **Shell Commands**: Execute shell commands with `!` prefix
- **File Inclusion**: Include file contents with `@` prefix

## Installation

```bash
pip install llm-supercli
```

Or install from source:

```bash
git clone https://github.com/llm-supercli/llm-supercli.git
cd llm-supercli
pip install -e .
```

## Quick Start

```bash
# Start the CLI
llm

# Or use the full command
llm-supercli
```

## Authentication

### Gemini (OAuth - gemini-cli compatible)

```bash
/login gemini
```

Credentials stored in `~/.gemini/oauth_creds.json`. Requires:
- Google Cloud project with Vertex AI API enabled
- Project ID in `~/.gemini/settings.json`

### Qwen (OAuth - qwen-cli compatible)

```bash
/login qwen
```

Credentials stored in `~/.qwen/oauth_creds.json`. Uses `chat.qwenlm.ai` API.
- Free tier: 2,000 requests/day, 60 requests/minute

### API Keys

Set environment variables for other providers:

```bash
export GROQ_API_KEY=your_key
export OPENROUTER_API_KEY=your_key
export TOGETHER_API_KEY=your_key
export HF_API_KEY=your_key
export GEMINI_API_KEY=your_key  # Alternative to OAuth
```

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help message |
| `/model` | Switch LLM model or provider (interactive menu) |
| `/settings` | View/edit settings (interactive menu) |
| `/login [provider]` | Login with OAuth (gemini, qwen, google, github) |
| `/logout [provider]` | Logout from provider |
| `/sessions` | List and manage chat sessions |
| `/new` | Start a new chat session |
| `/clear` | Clear the screen |
| `/status` | Show current status |
| `/cost` | Show token usage and costs |
| `/key [provider] [key]` | Set API key for provider |
| `/mcp` | Manage MCP server connections |
| `/quit` | Exit the CLI |

## Special Syntax

```bash
# Execute shell command
!ls -la

# Include file contents
@path/to/file.py

# Include with context
Tell me about @src/main.py
```

## Configuration

Settings are stored in `~/.llm_supercli/config.json`.

### Interactive Settings Menu

```bash
/settings
```

Navigate with arrow keys, select with Enter:
- **LLM Settings**: Provider, model, temperature, max_tokens
- **UI Settings**: Theme, streaming, syntax highlighting
- **MCP Settings**: Enable/disable MCP features

## Providers

| Provider | Models | Auth |
|----------|--------|------|
| Groq | llama-3.3-70b, mixtral-8x7b, gemma2-9b | API Key |
| OpenRouter | claude-3.5, gpt-4o, gemini-pro | API Key |
| Together | llama-3.1-405b, mixtral-8x22b | API Key |
| HuggingFace | llama-3-70b, mixtral-8x7b | API Key |
| Ollama | llama3.2, mistral, codellama | Local |
| Gemini | gemini-2.5-pro, gemini-2.0-flash | OAuth/API Key |
| Qwen | qwen3-235b, qwen-coder-plus | OAuth/API Key |

## Requirements

- Python 3.10+
- rich >= 13.0.0
- httpx >= 0.25.0
- click >= 8.0.0
- prompt_toolkit >= 3.0.0

## License

MIT License
