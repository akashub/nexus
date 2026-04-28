# Nexus

Personal learning knowledge graph. Capture concepts you're learning, get AI-generated explanations, and visualize how everything connects — all locally, zero cloud dependency.

Built for developers who encounter dozens of new tools, frameworks, and patterns while building software and want a way to map, understand, and retain them.

## What It Does

- **Add a concept** and Nexus auto-enriches it: fetches docs via Context7, generates a description and summary via local LLM, creates an embedding, and suggests connections to your existing knowledge.
- **Search** by keyword (FTS5) or semantic similarity (embedding cosine distance).
- **Ask questions** using your knowledge graph as context — answers reference your actual concepts and connections.
- **Visualize** your knowledge as an interactive graph with nodes, edges, and categories.
- **Works offline** — everything runs locally via Ollama. No API keys, no cloud accounts.

## Architecture

```
backend/          Python CLI + API server
  src/nexus/      Core package (CLI, DB, AI, API)
  migrations/     SQLite schema migrations
  tests/          pytest test suite
desktop/          Tauri v2 + React frontend (WIP)
```

**Stack:** Python 3.12+ / Click CLI / FastAPI / SQLite (WAL + FTS5) / Ollama / Tauri v2 / React + TypeScript / Cytoscape.js

## Quick Start

### Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com) running locally

### Install

```bash
cd backend
uv sync
uv run nexus db init
```

### Pull Models

```bash
ollama pull gemma4
ollama pull nomic-embed-text
```

### Add Your First Concept

```bash
uv run nexus add "React" --category framework
```

Nexus will fetch docs, generate a description, create an embedding, and suggest connections to existing concepts.

## CLI Reference

```
nexus add <name>              Add a concept (auto-enriches via Ollama)
  --category, -c              devtool | framework | concept | pattern | language
  --tags, -t                  Comma-separated tags
  --notes, -n                 Personal notes
  --no-enrich                 Skip AI enrichment

nexus connect <src> <tgt>     Create a directed edge
  --type, -t                  uses | depends_on | similar_to | part_of | related_to

nexus list                    List all concepts
  --category, -c              Filter by category
  --limit, -n                 Max results (default 20)
  --format                    table | json

nexus search <query>          Full-text search
  --semantic, -s              Use embedding similarity instead of FTS

nexus show <name>             Show full concept details + connections

nexus ask <question>          Ask a question using graph context (streams via Ollama)

nexus remove <name>           Remove a concept and its edges
  --yes, -y                   Skip confirmation

nexus serve                   Start the API server
  --port, -p                  Port (default 7777)
  --host                      Host (default 127.0.0.1)

nexus db init                 Initialize the database
```

## API

`nexus serve` starts a FastAPI server on `localhost:7777`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/concepts` | List concepts (query: `category`, `limit`) |
| GET | `/api/concepts/:id` | Get concept detail |
| POST | `/api/concepts` | Create concept (triggers enrichment) |
| PUT | `/api/concepts/:id` | Update concept fields |
| DELETE | `/api/concepts/:id` | Delete concept + cascading edges |
| GET | `/api/edges?concept_id=` | List edges for a concept |
| POST | `/api/edges` | Create edge |
| DELETE | `/api/edges/:id` | Delete edge |
| GET | `/api/search?q=&semantic=` | Search (FTS or semantic) |
| POST | `/api/ask` | Ask a question with graph context |
| GET | `/api/graph` | Full graph (nodes + edges) |
| GET | `/api/stats` | Concept count, edge count, categories |

## Development

```bash
cd backend

# Run tests
uv run pytest -q

# Lint
uv run ruff check src/ tests/

# Install in dev mode
uv sync
```

### Database

SQLite with WAL mode, stored at `~/.nexus/nexus.db`. FTS5 virtual table with auto-sync triggers keeps full-text search in sync.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXUS_LLM_MODEL` | `gemma4` | Ollama model for text generation |
| `NEXUS_EMBED_MODEL` | `nomic-embed-text` | Ollama model for embeddings |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |

## License

MIT
