# LLM SuperCLI

<div align="center">

![LLM SuperCLI](https://raw.githubusercontent.com/alisaalisaalisaalisas/LLM_SuperCLI/main/llm_supercli/llm.png)

**A powerful multi-provider LLM command line interface**

[![Version](https://img.shields.io/badge/version-1.0.21-blue.svg)](https://github.com/alisaalisaalisaalisas/LLM_SuperCLI)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

[Features](#features) • [Installation](#installation) • [Quick Start](#quick-start) • [Providers](#providers) • [Commands](#commands)

</div>

---

## Features

- **Multi-Provider Support** - Groq, OpenRouter, Together AI, HuggingFace, Ollama, Gemini, Qwen
- **Free Tiers Available** - Gemini, Qwen, and Ollama work without API keys
- **Interactive UI** - Rich terminal with autocomplete, syntax highlighting, and live streaming
- **Streaming Responses** - Real-time token streaming with reasoning display
- **Session Management** - Save, load, and manage conversation sessions
- **Tool Support** - Built-in file operations, shell commands, and directory navigation
- **MCP Integration** - Model Context Protocol server connections
- **Multiple Modes** - Code, chat, and other operational modes

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
git clone https://github.com/alisaalisaalisaalisas/LLM_SuperCLI.git
cd LLM_SuperCLI
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
| **Qwen** | coder-model, vision-model | OAuth | Free (2K req/day) |
| **Gemini** | gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite | OAuth | Free |
| **Groq** | llama-3.3-70b, llama-3.1-8b, mixtral-8x7b, gemma2-9b | API Key | Free tier |
| **Ollama** | llama3.2, mistral, codellama, phi3 | Local | Free |
| **OpenRouter** | claude-3.5-sonnet, gpt-4o, gemini-pro-1.5, llama-3.1-405b | API Key | Paid |
| **Together** | llama-3.1-405b, llama-3.1-70b, mixtral-8x22b | API Key | Paid |
| **HuggingFace** | llama-3-70b, mixtral-8x7b, gemma-7b | API Key | Paid |

---

## Authentication

### Qwen (Free - OAuth)

Uses Qwen Code CLI credentials:

```bash
npm install -g @anthropic-ai/qwen-code
qwen  # Follow OAuth flow
```

Credentials stored in `~/.qwen/oauth_creds.json`

**Free tier:** 2,000 requests/day, 60 requests/minute

### Gemini (Free - OAuth)

Uses Gemini CLI credentials:

```bash
npm install -g @anthropic-ai/gemini-cli
gemini  # Follow OAuth flow
```

Credentials stored in `~/.gemini/oauth_creds.json`

### Ollama (Free - Local)

Run models locally with Ollama:

```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.2
```

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
| `/account` | View account information |
| `/favorite` | Save session as favorite |
| `/compress` | Compress conversation context |
| `/rewind` | Rewind to previous message |
| `/quit` | Exit the CLI |
| `/update` | Check for updates and install |

---

## Updating

### From within the CLI

```bash
/update
```

This will check for new versions and prompt you to update if available.

### Manual update

```bash
# npm installation
npm update -g llm-supercli

# pip installation
pip install --upgrade llm-supercli
```

After updating, restart the CLI to use the new version.

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

## Built-in Tools

The LLM can use these tools during conversations:

| Tool | Description |
|------|-------------|
| `list_directory(path)` | List files and folders |
| `read_file(path)` | Read file contents |
| `write_file(path, content)` | Create or write a file |
| `create_directory(path)` | Create a folder |
| `run_command(command)` | Run shell command |
| `get_current_directory()` | Get current working directory |

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

**Dependencies:**
- rich >= 13.0.0
- httpx >= 0.25.0
- click >= 8.0.0
- prompt_toolkit >= 3.0.0
- packaging >= 21.0

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Links

- **GitHub:** https://github.com/alisaalisaalisaalisas/LLM_SuperCLI
- **npm:** https://www.npmjs.com/package/llm-supercli
- **PyPI:** https://pypi.org/project/llm-supercli/

---

<div align="center">

**Made with love for the CLI community**

</div>
