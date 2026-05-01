<p align="center">
  <img src="desktop/src-tauri/icons/128x128@2x.png" width="80" height="80" alt="Nexus">
</p>

<h1 align="center">Nexus</h1>

<p align="center">
  Personal knowledge graph for developers.<br>
  Capture every tool and framework you learn. Visualize how they connect.
</p>

<p align="center">
  <a href="https://akashub.github.io/nexus/">Website</a> &nbsp;·&nbsp;
  <a href="https://github.com/akashub/nexus/releases/latest">Download Desktop App</a> &nbsp;·&nbsp;
  <a href="docs/">Documentation</a>
</p>

---

## What is Nexus?

You learn dozens of tools while building software — frameworks, CLI tools, patterns, libraries. Nexus captures them into a searchable, visual knowledge graph that grows with you.

- **Passive capture** — hooks watch your `npm install`, `pip install`, `brew install` commands and scan your project files automatically
- **AI enrichment** — fetches docs, generates descriptions, creates embeddings, and suggests connections using any local Ollama model
- **Interactive graph** — desktop app renders your entire stack as a draggable, filterable knowledge graph
- **Claude Code integration** — MCP server gives Claude direct access to your knowledge graph during sessions
- **Works offline** — everything runs locally, no API keys required

## Install

### CLI

```bash
pip install nexus-graph
```

or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install nexus-graph
```

### From source

```bash
git clone https://github.com/akashub/nexus.git
cd nexus/backend
uv tool install .
```

### Desktop app

Download from the [releases page](https://github.com/akashub/nexus/releases/latest) — available for macOS, Linux, and Windows.

## Quick start

```bash
# Initialize the database
nexus db init

# Wire into Claude Code (MCP server + hooks + skill)
nexus mcp install

# Scan an existing project
nexus scan . --enrich

# Optional: pull a local AI model (any Ollama model works)
ollama pull gemma3
ollama pull nomic-embed-text
```

That's it. Your graph builds itself from here — hooks capture installs, session-end scans catch changes, and Claude logs new tools as you work.

## Verify

```bash
nexus status
```

Green checks for Database, MCP Server, Hooks, Skill. Ollama shows red if not running — that's fine, it's optional.

## Key commands

| Command | What it does |
|---------|-------------|
| `nexus add "React"` | Add a concept with AI enrichment |
| `nexus scan .` | Scan project for dependencies |
| `nexus search "testing"` | Full-text search |
| `nexus search "testing" -s` | Semantic search (embedding similarity) |
| `nexus ask "How does X relate to Y?"` | Ask questions using graph context |
| `nexus onboard` | See your expertise profile |
| `nexus gaps` | Detect missing tools in your stack |
| `nexus serve` | Start API server for desktop app |

## Documentation

| Page | Contents |
|------|----------|
| **[CLI Reference](docs/cli-reference.md)** | All commands, flags, and options |
| **[Claude Code Integration](docs/claude-code-integration.md)** | MCP server, hooks, skill, passive capture, ledger format |
| **[API Reference](docs/api-reference.md)** | REST endpoints for the local server |
| **[Configuration](docs/configuration.md)** | Environment variables, AI models, database |
| **[Usage Guide](docs/usage-guide.md)** | Workflows, team scenarios, tips |

## How AI enrichment works

Nexus uses **any Ollama model** for enrichment — not just one specific model. Set `NEXUS_LLM_MODEL` to whatever you have installed (`llama3`, `mistral`, `phi3`, `gemma3`, `gemma4`, etc.). Cloud APIs (Anthropic, OpenAI) work too via optional env vars.

The enrichment pipeline:
1. Fetch docs via Context7, PyPI, npm, GitHub
2. Generate description and summary via your chosen model
3. Create embedding via nomic-embed-text
4. Find related concepts by cosine similarity
5. Suggest connections

See [Configuration](docs/configuration.md) for model setup details.

## Development

```bash
cd backend
uv sync
uv run pytest -q
uv run ruff check
```

## License

MIT
