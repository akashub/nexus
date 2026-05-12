---
name: nexus
description: Maintain the developer's personal knowledge graph. MUST call onboard at session start and add_concept when new tools appear.
---

# Nexus — Session Rules

## Session Start (REQUIRED)

Call `nexus.onboard(project_dir)` on your FIRST tool call of every session.
This tells you what the developer knows well, has seen, and is missing.

If the graph has < 5 concepts for a project with code, say:
> "Your Nexus graph is sparse. Want me to scan the project and populate it?"

If yes: read package.json/pyproject.toml, CLAUDE.md, Dockerfiles, and key
source files. Call `nexus.add_concept()` for each tool/framework with a
description written from YOUR knowledge of the codebase — not generic docs.

## During Session (REQUIRED)

Call `nexus.add_concept()` IMMEDIATELY when any of these happen:
- A new package is installed (`npm install`, `pip install`, etc.)
- A tool or framework is discussed in depth for the first time
- You explain a concept the developer didn't know before
- Architecture decisions are made (new module, new pattern, new service)

Do NOT batch these to session end. Add them as they come up.

### How to write a good concept

```
nexus.add_concept(
  name="playwright",
  project_dir="/absolute/path/to/project",
  category="devtool",  // devtool | framework | concept | pattern | language
  description="E2E testing framework used in this project for auth flow tests. Chosen over Cypress for multi-browser support and auto-waiting.",
  summary="E2E browser testing with auto-wait",
  quickstart="npm install -D @playwright/test\nnpx playwright install",
  relationships=[{"target": "react", "type": "tested_with"}],
  overwrite=true  // replace existing fields when you have better context
)
```

Default behavior fills empty fields only. `overwrite=true` replaces existing
fields — use it when you have real project context and the current description
is generic or wrong.

The description should say what it IS and why THIS PROJECT uses it.
Not generic docs. Not "FastAPI is a modern web framework." Instead:
"FastAPI backend serving the chat gateway API. Runs on uvicorn behind Docker."

### Relationship types
uses, depends_on, similar_to, part_of, tested_with, configured_by,
builds_into, wraps, serves, deployed_via, replaces

## Proactive Features

- `nexus.detect_gaps(project_dir)` — finds missing companion tools for
  the project's stack. Offer this after bootstrap or when the developer
  asks "what should I learn next?"
- `nexus.get_journey(project_dir)` — shows learning progress over time.
  Use when asked "what have I learned?" or "show my progress."

## Before Explaining a Tool

Call `nexus.get_concept_detail(name)` first. If the developer knows it
well (has description + edges), skip the basics and go deeper.

## Search

`nexus.search_concepts(query)` — keyword search across the graph.
Use when the developer asks "what do I know about X" or "have I used X."

## What NOT to Capture
- Standard library (fs, path, os, collections)
- Concepts already in graph with good descriptions (check first)
- Trivial one-off utilities
