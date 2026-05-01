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

### Capture
- `nexus.add_concept(name, project_dir, category)` — add a concept manually
- `nexus.track_install(name, source, project_dir)` — record an install
  (PostToolUse hook does this automatically for npm/pip/brew/cargo installs)

## When to Use

- **Session start**: Call `onboard` to understand what the developer knows
- **Before explaining a tool**: Check `get_concept_detail` — if known_well, skip basics
- **When developer asks "what do I know about X"**: Use `search_concepts`
- **When suggesting tools**: Check `get_expertise` to avoid suggesting things
  the developer already knows well

## Knowledge Ledger (session-end capture)

Before your final response in every session, write a knowledge ledger file
at `/tmp/nexus-ledger.jsonl`. One JSON line per concept that was introduced,
discussed, or installed during the session.

Write RICH entries — you have the full session context, so include everything
Nexus needs to build the graph without calling Ollama:

```jsonl
{"name": "playwright", "description": "E2E testing framework with multi-browser support and auto-waiting", "summary": "E2E browser testing with auto-wait", "category": "devtool", "project_dir": "/path/to/project", "relationships": [{"target": "vitest", "type": "tested_with"}, {"target": "react", "type": "uses"}], "context": "Added for auth flow E2E tests"}
```

### Fields
- `name` (required): package/tool/concept name
- `description`: 2-3 sentence technical description. YOU know why it was
  added — include that context, not just what docs say.
- `summary`: one-line summary under 15 words
- `category`: one of devtool, framework, concept, pattern, language
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
