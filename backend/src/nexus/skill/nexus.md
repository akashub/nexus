---
name: nexus
description: Query and update the Nexus personal knowledge graph. Tracks tools, frameworks, and concepts across projects.
---

# Nexus Knowledge Graph

Nexus is a personal developer knowledge graph. It tracks tools, frameworks,
and concepts you learn across projects.

## Available MCP Tools

### Onboarding (start of session)
- `nexus.onboard(project_dir)` — get expertise profile for current project
  Shows what you know well, what you've seen, and what's missing.
  Use this at session start to understand the developer's context.

### Search & Lookup
- `nexus.search_concepts(query)` — find concepts by keyword
- `nexus.get_concept_detail(name)` — full detail including description, quickstart, edges

### Projects
- `nexus.list_projects()` — see all tracked projects

### Capture (use during the session, not just at end)
- `nexus.add_concept(name, project_dir, category, description, summary,
  quickstart, notes, relationships)` — add or enrich a concept with full detail.
  If the concept already exists, fills in any empty fields without overwriting.
  `relationships`: `[{"target": "react", "type": "uses"}]`
- `nexus.track_install(name, source, project_dir)` — record an install
  (PostToolUse hook does this automatically for npm/pip/brew/cargo installs)

## When to Use

- **Session start**: Call `onboard` to understand what the developer knows
- **Before explaining a tool**: Check `get_concept_detail` — if known_well, skip basics
- **When developer asks "what do I know about X"**: Use `search_concepts`
- **When suggesting tools**: Check `get_expertise` to avoid suggesting things
  the developer already knows well
- **When a new tool/framework is introduced or installed**: Call `add_concept`
  immediately with full detail — don't wait for session end
- **When discussing a concept in depth**: Enrich it via `add_concept` with
  description, quickstart, and relationships to other known concepts

## First Run — Bootstrap

When `onboard` returns an empty or very sparse graph (< 5 concepts) for a
project that clearly has existing code, offer to bootstrap the knowledge graph:

> "Your Nexus graph is empty but this project already uses several tools.
> Want me to scan the project and populate your knowledge graph?"

If the user agrees:

1. **Scan declared dependencies** — read package.json, pyproject.toml,
   Cargo.toml, go.mod, Gemfile, requirements.txt, etc.
2. **Scan config files** — Dockerfile, docker-compose.yml, CI configs
   (.github/workflows/), tailwind.config, tsconfig.json, vite.config, etc.
3. **Scan imports** — skim key source files for major frameworks/libraries
   actually used (not just declared).
4. **Write a ledger file** — for every tool/framework/concept found, write a
   rich entry to `/tmp/nexus-ledger.jsonl` with description, category,
   quickstart, and relationships between them. Use YOUR knowledge of these
   tools — you have full context from reading the codebase.
5. **Ingest** — call `nexus ingest /tmp/nexus-ledger.jsonl` via shell to
   import everything in one batch.

Write entries for 10–30 concepts depending on project size. Focus on things
the developer would actually want to recall: frameworks, major libraries,
dev tools, deployment targets, architectural patterns. Skip trivial utils
and standard library modules.

After bootstrap, call `onboard` again to confirm the graph is populated and
show the developer their expertise profile.

## Capture Strategy

**Primary: call `add_concept` via MCP during the session.** Every time a new
tool, framework, or concept comes up — add it immediately with description,
summary, quickstart, and relationships. This writes to the graph in real time.
Don't batch everything to session end.

**Fallback: write a ledger file at session end.** For anything you didn't
capture via MCP (bulk bootstrap, concepts discovered late), write a ledger
file at `/tmp/nexus-ledger.jsonl`. The SessionEnd hook auto-ingests it.

One JSON line per concept:

```jsonl
{"name": "playwright", "description": "E2E testing framework with multi-browser support and auto-waiting", "summary": "E2E browser testing with auto-wait", "category": "devtool", "quickstart": "npm install -D @playwright/test\nnpx playwright install\nnpx playwright test", "project_dir": "/path/to/project", "relationships": [{"target": "vitest", "type": "tested_with"}, {"target": "react", "type": "uses"}], "context": "Added for auth flow E2E tests"}
```

### Fields
- `name` (required): package/tool/concept name
- `description`: 2-3 sentence technical description. YOU know why it was
  added — include that context, not just what docs say.
- `summary`: one-line summary under 15 words
- `category`: one of devtool, framework, concept, pattern, language
- `quickstart`: installation commands and basic setup steps. Include the
  actual install command (npm install, pip install, etc.) and minimal
  getting-started steps. This is stored on the node for future reference.
- `project_dir`: absolute path to the project
- `relationships`: array of `{target, type}` where type is one of:
  uses, depends_on, similar_to, part_of, tested_with, configured_by,
  builds_into, wraps, serves, deployed_via, replaces
- `context`: free-text note about WHY this was added or HOW it's used

### What to capture
- Packages installed during the session (npm install, pip install, etc.)
- Tools or frameworks discussed in depth
- Architectural patterns introduced (e.g. "event sourcing", "CQRS")
- Concepts the developer learned about

### What NOT to capture
- Standard library features (fs, path, os)
- Concepts already in the graph with good descriptions (check via MCP)
- Trivial utils that don't warrant a graph node
