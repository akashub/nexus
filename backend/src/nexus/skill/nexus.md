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
