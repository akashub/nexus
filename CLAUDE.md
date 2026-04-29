# Nexus

Personal learning knowledge graph. Capture concepts, understand them with local AI, visualize connections. Desktop app + CLI, powered by Ollama. Zero cloud dependency.

## Hard rules
- Every file <= 200 LOC. Refactor, never bypass.
- pytest for Python, vitest for React. No skipped tests without a linked issue.
- No secrets in code. Load from env.
- Prefer editing existing files over creating new ones.
- No emoji unless user explicitly asks.
- Ollama calls must degrade gracefully — if Ollama is not running, warn and continue without AI. The app must always work without AI.

## Stack
- **Monorepo**: `backend/` (Python) + `desktop/` (Tauri + React).
- **Backend**: Python 3.12+. FastAPI (async) + uvicorn for local API server. Click for CLI.
- **Database**: SQLite (WAL mode) + FTS5 for full-text search. DB lives at `~/.nexus/nexus.db`.
- **AI**: Ollama (local). Primary model `gemma4:e2b` for generation, `nomic-embed-text` for embeddings. Model names read from env (`NEXUS_LLM_MODEL`, `NEXUS_EMBED_MODEL`).
- **Docs fetch**: Context7 MCP as primary source for library/framework docs. Web fetch (`httpx`) as fallback.
- **Desktop**: Tauri v2 (Rust shell + OS webview). React + TypeScript frontend.
- **Graph viz**: Cytoscape.js for interactive knowledge graph rendering.
- **Styling**: Tailwind CSS. Dark theme only for V1.
- **Package management**: uv for Python, pnpm for Node/React.

## Development workflow (mandatory)
Every change follows this pipeline. No shortcuts.

1. **Requirement** — understand the ask, clarify ambiguities.
2. **Plan** — create or update plan in `plans/` with Objective, Acceptance criteria, Steps.
3. **Tasks + Acceptance criteria + Test cases** — break plan into discrete tasks with measurable criteria and test cases for each.
4. **Implement** — write code following the plan and tasks.
5. **Run test cases** — all must pass: no linter errors, no type errors, no build errors, no warnings (`uv run pytest -q` backend, `pnpm test` desktop).
6. **Run anti-slop skill** — `/eagle-anti-slop` on changed files to eliminate AI-generated slop.
7. **Run spectral agents** — clear all severity levels (critical, high, medium, low, nits).
8. **Lint** — `uv run ruff check` (Python), `pnpm lint` (TypeScript). Zero warnings.
9. **Commit to git** — discrete bisectable commits with Conventional Commits (`feat()`, `fix()`, `docs()`, etc.).
10. **Push to GitHub** — push with `GH_TOKEN` for akashub account.
11. **Post-push** — if successful: update wiki (llm-wiki + Obsidian), update task list, create memories if needed. Move to next task.

## Directory layout
```
backend/
  src/nexus/          Python package
    __init__.py
    cli.py            CLI entry point (Click)
    db.py             SQLite operations + migrations
    models.py         Dataclasses (Concept, Edge, Resource, Conversation)
    ai.py             Ollama client (generate, embed, is_available)
    fetch.py          Context7 + web fetch client
    server.py         FastAPI local server
  migrations/         Numbered SQL migration files
  tests/              pytest tests
desktop/
  src/                React + TypeScript frontend
    components/       GraphView, SidePanel, SearchBar, ChatPanel, AddModal
    hooks/            useApi, useGraph, useSearch
    types.ts          TypeScript types matching Python models
  src-tauri/          Rust/Tauri shell (minimal — mostly scaffold)
plans/                Session plans
```

## API server
`nexus serve` starts FastAPI on `localhost:7777`. Desktop app auto-starts this on launch, stops on quit.

Endpoints:
- `GET/POST /api/concepts` — list/create
- `GET/PUT/DELETE /api/concepts/:id` — detail/update/delete
- `GET/POST /api/edges` — list/create
- `DELETE /api/edges/:id` — delete
- `GET /api/search?q=...&semantic=bool` — search
- `POST /api/ask` — chat with graph context
- `GET /api/graph` — full nodes + edges for visualization
- `GET /api/stats` — counts and category breakdown

## CLI commands
- `nexus add <name>` — add concept (enriches via Ollama by default, `--no-enrich` to skip)
- `nexus connect <source> <target>` — create edge (`--type` for relationship)
- `nexus list` — list concepts (`--category`, `--format json`)
- `nexus search <query>` — FTS5 search (`--semantic` for embedding similarity)
- `nexus show <name>` — full concept detail
- `nexus ask <question>` — chat with graph context via Ollama
- `nexus remove <name>` — delete concept + cascading edges
- `nexus serve` — start API server (`--port`, `--host`)
- `nexus db init` — initialize database

## SQLite conventions
- PRAGMAs set per-connection: `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`, `foreign_keys=ON`.
- FTS5 tables use triggers for auto-sync (INSERT/UPDATE/DELETE).
- Migrations are numbered `.sql` files in `backend/migrations/`. Applied idempotently on `db init` and server startup.

## Enrichment pipeline (on `nexus add`)
1. Resolve via Context7 → if library found, fetch docs.
2. If no Context7 match → optional web fetch fallback.
3. Gemma-4B summarizes (2-3 sentences + one-liner).
4. Gemma-4B suggests category.
5. nomic-embed-text generates embedding vector.
6. Cosine similarity finds top-3 related existing concepts → suggest connections.
7. All stored in concepts table. User confirms suggested connections.

## Out of scope (V1)
Polyglot voice integration, cloud model toggle, gap detection, learning journey view, Obsidian sync, cross-platform packaging/signing, multi-graph support.
