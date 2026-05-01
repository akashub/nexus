# Nexus

Personal learning knowledge graph. Capture concepts you're learning, get AI-generated explanations, and visualize how everything connects — all locally, zero cloud dependency.

Built for developers who encounter dozens of new tools, frameworks, and patterns while building software and want a way to map, understand, and retain them.

## Install

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [Ollama](https://ollama.com) running locally (optional — everything works without it, just no AI enrichment)

### From GitHub

```bash
# Install with uv (recommended)
uv tool install "git+https://github.com/akashub/nexus.git#subdirectory=backend"

# Or with pip
pip install "git+https://github.com/akashub/nexus.git#subdirectory=backend"
```

### From source

```bash
git clone https://github.com/akashub/nexus.git
cd nexus/backend
uv tool install .
```

### Pull Ollama models (optional)

```bash
ollama pull gemma4
ollama pull nomic-embed-text
```

### Initialize the database

```bash
nexus db init
```

### Verify installation

```bash
nexus status
```

You should see all green checks for Database, MCP Server, Hooks, Skill, and Ollama (Ollama shows red if not running — that's fine, it's optional).

## Claude Code Integration

This is where Nexus shines. One command wires everything into Claude Code:

```bash
nexus mcp install
```

This installs three things:

| Component | What it does | Where it lives |
|-----------|-------------|----------------|
| **MCP Server** | Gives Claude read/write access to your knowledge graph during sessions | `~/.claude.json` |
| **Hooks** | Auto-captures package installs (PostToolUse) and runs scan + ingest on session end (SessionEnd) | `~/.claude/settings.json` |
| **Skill** | Teaches Claude the ledger format so it logs new tools/frameworks as you work | `~/.claude/skills/nexus/SKILL.md` |

After installing, use `/nexus` in Claude Code to interact with your graph.

### How passive capture works

1. You work normally in Claude Code
2. Claude notices new tools/frameworks and writes entries to `/tmp/nexus-ledger.jsonl`
3. The PostToolUse hook catches `npm install`, `pip install`, `brew install`, `cargo add` commands
4. When the session ends, the SessionEnd hook runs `nexus ingest` (processes the ledger) and `nexus scan` (reads package files)
5. Your knowledge graph grows automatically

### Check integration status

```bash
nexus mcp install --check   # quick check
nexus status                # full status with DB stats
```

### Uninstall from Claude Code

```bash
nexus mcp install --uninstall
```

## What It Does

- **Passive capture** — hooks + skill automatically log what you use across Claude Code sessions
- **Project scanning** — `nexus scan .` reads package.json, requirements.txt, pyproject.toml, Cargo.toml, Dockerfiles, CI configs
- **AI enrichment** — fetches docs via Context7, generates descriptions via local LLM, creates embeddings, suggests connections
- **Search** — keyword (FTS5) or semantic similarity (embedding cosine distance)
- **Ask questions** — uses your knowledge graph as context for answers via Ollama
- **Expertise profiling** — `nexus onboard` shows what you know well, what you've seen, and gaps per project
- **Visualize** — desktop app renders an interactive graph (optional)
- **Works offline** — everything runs locally. No API keys, no cloud accounts

## CLI Reference

### Core commands

```
nexus add <name>              Add a concept (auto-enriches via Ollama)
  --category, -c              devtool | framework | concept | pattern | language
  --tags, -t                  Comma-separated tags
  --notes, -n                 Personal notes
  --no-enrich                 Skip AI enrichment
  --source, -s                Doc source: auto | all | context7 | pypi | npm | github | libraries

nexus connect <src> <tgt>     Create a directed edge
  --type, -t                  uses | depends_on | similar_to | part_of | related_to | ...

nexus list                    List all concepts
  --category, -c              Filter by category
  --limit, -n                 Max results (default 20)
  --format                    table | json

nexus search <query>          Full-text search
  --semantic, -s              Use embedding similarity instead of FTS

nexus show <name>             Show full concept details + connections
nexus ask <question>          Ask a question using graph context (streams via Ollama)
nexus remove <name>           Remove a concept and its edges
```

### Project commands

```
nexus scan <path>             Scan a project directory for deps and tools
  --enrich                    Also run AI enrichment on discovered concepts
  --dry-run                   Show what would be added without changing DB

nexus project list            List all tracked projects
nexus project add <name>      Add a project manually
nexus project show <name>     Show project details
nexus project remove <name>   Remove a project and its concepts

nexus compact [project]       Merge duplicates, remove stale entries
  --all                       Compact all projects
  --dry-run                   Preview only

nexus replicate <project>     Generate a setup script to recreate a project's toolchain
  --mode                      complete | context

nexus onboard                 Show expertise profile (known_well / seen / gaps)
  --project                   Filter to a specific project
```

### AI commands

```
nexus enrich-relationships    Infer edges between concepts using embeddings + AI
nexus cluster                 Assign semantic groups to concepts using AI
```

### Integration commands

```
nexus mcp install             Install MCP server, hooks, and skill into Claude Code
nexus mcp install --check     Check installation status
nexus mcp install --uninstall Remove Nexus from Claude Code
nexus mcp serve               Start the MCP server (used by Claude Code, not run manually)

nexus ingest <file.jsonl>     Import a knowledge ledger file
nexus track <name>            Track a package install
  --source                    npm | pip | brew | cargo

nexus status                  Show full integration status
nexus serve                   Start the API server (for desktop app)
nexus db init                 Initialize / migrate the database
```

## Desktop App (Optional)

The desktop app visualizes your knowledge graph. It's not required — the CLI + Claude Code integration is fully functional without it.

```bash
cd desktop
pnpm install
pnpm tauri dev
```

Requires the API server running (`nexus serve`).

## API

`nexus serve` starts a FastAPI server on `localhost:7777`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/concepts` | List concepts |
| GET | `/api/concepts/:id` | Concept detail |
| POST | `/api/concepts` | Create concept (triggers enrichment) |
| PUT | `/api/concepts/:id` | Update concept |
| DELETE | `/api/concepts/:id` | Delete concept + edges |
| GET | `/api/edges?concept_id=` | List edges for a concept |
| POST | `/api/edges` | Create edge |
| DELETE | `/api/edges/:id` | Delete edge |
| GET | `/api/search?q=&semantic=` | Search (FTS or semantic) |
| POST | `/api/ask` | Ask with graph context |
| GET | `/api/graph` | Full graph (nodes + edges) |
| GET | `/api/graph/global` | Projects as nodes with shared-dep edges |
| GET | `/api/stats` | Counts and category breakdown |
| GET/POST | `/api/projects` | List/create projects |
| POST | `/api/projects/:id/scan` | Trigger project scan |
| POST | `/api/projects/:id/replicate` | Generate setup script |
| GET | `/api/projects/:id/expertise` | Expertise profile |

## Knowledge Ledger Format

Claude Code writes entries to `/tmp/nexus-ledger.jsonl` during sessions. Each line is a JSON object:

```json
{"name": "zod", "description": "TypeScript-first schema validation with static type inference", "summary": "Schema validation + type inference", "category": "library", "context": "Added for API request validation in the Express backend", "project_dir": "/path/to/project", "relationships": [{"target": "typescript", "type": "depends_on"}, {"target": "express", "type": "uses"}]}
```

Fields:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Tool, framework, or concept name |
| `description` | no | What it is |
| `summary` | no | One-liner |
| `category` | no | devtool, framework, library, concept, pattern, language |
| `context` | no | Why it was used in this session (stored as `notes`) |
| `project_dir` | no | Project directory path |
| `relationships` | no | Array of `{target, type}` objects |

Valid relationship types: `uses`, `depends_on`, `similar_to`, `part_of`, `tested_with`, `configured_by`, `builds_into`, `wraps`, `serves`, `deployed_via`, `replaces`, `related_to`, `sends_data_to`, `triggers`

The SessionEnd hook runs `nexus ingest` to process the ledger into the graph. Entries that fail to parse are skipped; the file is deleted only if all entries succeed.

## Development

```bash
cd backend
uv sync
uv run pytest -q         # run tests
uv run ruff check        # lint
uv run nexus status      # check everything works
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXUS_LLM_MODEL` | `gemma4` | Ollama model for text generation |
| `NEXUS_EMBED_MODEL` | `nomic-embed-text` | Ollama model for embeddings |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |

### Database

SQLite with WAL mode at `~/.nexus/nexus.db`. FTS5 virtual table with auto-sync triggers. Migrations in `backend/migrations/`, applied idempotently on `nexus db init`.

## License

MIT
