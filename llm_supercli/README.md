# LLM SuperCLI

<div align="center">

```
 ██╗     ██╗     ███╗   ███╗   ███████╗██╗   ██╗██████╗ ███████╗██████╗  ██████╗██╗     ██╗
 ██║     ██║     ████╗ ████║   ██╔════╝██║   ██║██╔══██╗██╔════╝██╔══██╗██╔════╝██║     ██║
 ██║     ██║     ██╔████╔██║   ███████╗██║   ██║██████╔╝█████╗  ██████╔╝██║     ██║     ██║
 ██║     ██║     ██║╚██╔╝██║   ╚════██║██║   ██║██╔═══╝ ██╔══╝  ██╔══██╗██║     ██║     ██║
 ███████╗███████╗██║ ╚═╝ ██║   ███████║╚██████╔╝██║     ███████╗██║  ██║╚██████╗███████╗██║
 ╚══════╝╚══════╝╚═╝     ╚═╝   ╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝
```

**A powerful multi-provider LLM command line interface**

[![Version](https://img.shields.io/npm/v/llm-supercli.svg)](https://www.npmjs.com/package/llm-supercli)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

[Features](#features) • [Installation](#installation) • [Quick Start](#quick-start) • [Providers](#providers) • [Commands](#commands)

</div>

---

## Features

- **Multi-Provider Support** - Groq, OpenRouter, Together AI, HuggingFace, Ollama, Gemini, Qwen
- **Free Tiers Available** - Gemini and Qwen offer free OAuth authentication
- **Interactive UI** - Rich terminal with autocomplete, syntax highlighting, and interactive menus
- **Streaming Responses** - Real-time token streaming for all providers
- **Session Management** - Save, load, and manage conversation sessions
- **Tool Support** - Built-in file operations, shell commands, and directory navigation
- **MCP Integration** - Model Context Protocol server connections

---

## Installation

### Via npm (Recommended)

```bash
npm install -g llm-supercli
```

### Via pip

```bash
pip install llm-supercli
```

### From Source

```bash
git clone https://github.com/llm-supercli/llm-supercli.git
cd llm-supercli
pip install -e .
```

---

## Quick Start

```bash
# Start the CLI
llm

# Or use the full command
llm-supercli
```

---

## Providers

| Provider | Models | Auth | Cost |
|----------|--------|------|------|
| **Qwen** | coder-model, vision-model | OAuth | Free |
| **Gemini** | gemini-2.5-pro, gemini-2.5-flash | OAuth | Free |
| **Groq** | llama-3.3-70b, mixtral-8x7b, gemma2-9b | API Key | Free tier |
| **Ollama** | llama3.2, mistral, codellama, phi3 | Local | Free |
| **OpenRouter** | claude-3.5, gpt-4o, gemini-pro | API Key | Paid |
| **Together** | llama-3.1-405b, mixtral-8x22b | API Key | Paid |
| **HuggingFace** | llama-3-70b, mixtral-8x7b | API Key | Paid |

---

## Authentication

### Qwen (Free - OAuth)

Uses Qwen Code CLI credentials. Install and login via:

```bash
npm install -g @qwen-code/qwen-code
qwen  # Follow OAuth flow
```

Credentials stored in `~/.qwen/oauth_creds.json`

**Free tier:** 2,000 requests/day, 60 requests/minute

### Gemini (Free - OAuth)

Uses Gemini CLI credentials. Install and login via:

```bash
npm install -g @anthropic-ai/gemini-cli
gemini  # Follow OAuth flow
```

Credentials stored in `~/.gemini/oauth_creds.json`

### API Keys

Set environment variables for API key providers:

```bash
export GROQ_API_KEY=your_key
export OPENROUTER_API_KEY=your_key
export TOGETHER_API_KEY=your_key
export HF_API_KEY=your_key
```

Or set via CLI:

```bash
/key groq your_api_key
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help message |
| `/model` | Switch LLM model or provider |
| `/settings` | View/edit settings |
| `/login [provider]` | Login with OAuth |
| `/logout [provider]` | Logout from provider |
| `/sessions` | Manage chat sessions |
| `/new` | Start new chat session |
| `/clear` | Clear the screen |
| `/status` | Show current status |
| `/cost` | Show token usage |
| `/key [provider] [key]` | Set API key |
| `/mcp` | Manage MCP servers |
| `/quit` | Exit the CLI |

---

## Special Syntax

```bash
# Execute shell command
!ls -la
!git status

# Include file contents in prompt
@path/to/file.py
Tell me about @src/main.py

# Multiple files
Explain the difference between @file1.py and @file2.py
```

---

## Configuration

Settings stored in `~/.llm_supercli/config.json`

Access interactive settings menu:

```bash
/settings
```

**Available settings:**
- LLM: Provider, model, temperature, max_tokens
- UI: Theme, streaming, syntax highlighting
- MCP: Enable/disable MCP features

---

## Requirements

- Python 3.10+
- Node.js 14+ (for npm installation)

**Python dependencies:**
- rich >= 13.0.0
- httpx >= 0.25.0
- click >= 8.0.0
- prompt_toolkit >= 3.0.0
- pyfiglet

---

## License

MIT License

---

<div align="center">

**Made with love for the CLI community**

</div>
