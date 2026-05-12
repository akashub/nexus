# Graph Quality Overhaul

## Objective

Fix the 4 structural bugs, clean junk data, separate canonical vs personal context, and make the graph actually useful across all 3 projects (inventory_management, farmerchat-agentic, nexus).

## Current state (audit results)

- 89 concepts, 94 edges across 4 projects
- 27 junk concepts (eagle-* skills, generic terms like "Auth", "Framework", "Memory")
- 64 similarity edges (noise — same-category embedding matches), 26 inferred, 4 structural
- 0 cross-project edges despite 8 shared deps (uvicorn, pydantic, etc.)
- 6 hallucinated descriptions (e.g. nexus="Django admin panel")
- `description` field mixes canonical docs with personal session context

## Bugs to fix

1. **eagle_mem scanner dumps global tools** — `_scan_claude_tools()` adds every `~/.claude/skills/` and `~/.claude/plugins/cache/` directory as a project concept
2. **Cross-project concept ownership** — `sync.py:53-54` silently skips concepts already owned by another project instead of creating cross-project edges
3. **Relationship sync is project-scoped only** — `sync.py:100-105` uses `get_concept_by_name_and_project()` which drops all edges where either end belongs to a different project
4. **Generic terms leak through scanner** — `claude_md.py` `_SKIP_GENERIC` set missing "i18n", "Geocoding", "Phase planning", "Prompts", "Memory", "LLM routing", etc.

## Architecture change: separate context layers

Add `usage_context` field (column already exists as `usage_summary`). Split enrichment:
- `description` = canonical docs only (Context7/PyPI/npm/GitHub)
- `usage_summary` = personal context (Eagle Mem sessions, Claude memories, AI tool configs)
- Enrichment LLM prompt gets only docs for description generation
- Separate LLM call (or raw assembly) for usage_summary from session data

## Steps

### Step 1: Clean junk data from DB
Delete 27 junk concepts (eagle-* skills, claude-plugins-official, llm-wiki, generic terms). Delete all edges touching deleted concepts. This gives us a clean baseline to measure against.

**Acceptance:** concept count drops from 89 to ~62. No orphaned edge references.

### Step 2: Fix Bug 1 — remove `_scan_claude_tools()`
Remove the function and its call from `scan_eagle_mem()`. Global Claude tools are environment-level, not project concepts.

**Acceptance:** `scan_eagle_mem()` no longer returns eagle-* or claude-plugins-* concepts. Existing scanner tests pass.

### Step 3: Fix Bug 4 — expand `_SKIP_GENERIC` in claude_md.py
Add missing generic terms: "i18n", "geocoding", "routing", "phase planning", "prompts", "memory", "llm routing", "deployment", "phase", "auth", "repo", "real-time", "offline/pwa", "framework".

**Acceptance:** Scanning inventory_management's CLAUDE.md no longer produces "Auth", "Framework", "i18n", etc.

### Step 4: Fix Bug 3 — global fallback in `_sync_relationships()`
When `get_concept_by_name_and_project()` returns None, fall back to `get_concept()` (global name lookup). This allows structural edges to connect concepts across projects.

**Acceptance:** Scanning a project that uses "fastapi" (owned by nexus project) creates an edge to the existing fastapi concept.

### Step 5: Fix Bug 2 — cross-project edge creation in sync
When a scanned concept already exists under another project, create a "uses" edge from the current project's root concept (or a shared-dep marker) instead of silently skipping.

**Acceptance:** farmerchat-agentic scanning uvicorn (owned by nexus) creates a cross-project edge.

### Step 6: Separate context layers in enrichment
Modify `enrich.py` prompt to use only canonical docs for `description`. Add a second pass that writes Eagle Mem / session context to `usage_summary`. Update `_ENRICH_PROMPT` to exclude workflow context from description generation.

**Acceptance:** After re-enriching a concept, `description` contains only canonical info. `usage_summary` contains project-specific usage.

### Step 7: Tune similarity pass
Add guard in `infer.py:similarity_pass()`: skip pairs where both concepts share a common package-name prefix (e.g. `@tauri-apps/api` and `@tauri-apps/cli` are obviously related — don't waste a similarity edge). Also consider raising threshold from 0.7 to 0.75.

**Acceptance:** Re-running similarity pass produces fewer noise edges. Scoped-package siblings get structural "part_of" edges from scanner instead.

### Step 8: Re-scan all projects and measure
Run `nexus scan` on all 3 projects. Compare concept count, edge breakdown (structural/similarity/inferred), cross-project edges. Produce before/after scorecard.

**Acceptance:** Structural edges > 20% of total. Cross-project edges > 0. No junk concepts reintroduced.

### Step 9: Run anti-slop on all changed files
`/eagle-anti-slop` on all modified backend files.

### Step 10: Run spectral review
Full spectral suite on changed files.

### Step 11: Lint, commit, push
`uv run ruff check`, commit with conventional commits, push.
