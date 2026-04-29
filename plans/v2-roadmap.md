# Nexus V2+ Roadmap

## Vision
Nexus evolves from "manually add concepts" to a living dev environment graph that auto-captures tools, dependencies, and patterns from active Claude Code sessions. Three pillars: auto-capture, smart enrichment, environment replication.

## Pillar 1: Auto-Capture from Claude Code Sessions

**Claude Code Skill/Hook** that detects installs and additions during sessions.

- Detect `npm install`, `pip install`, `brew install`, MCP server setup, CLI tool additions
- Auto-call `nexus add` with context from the session
- Background categorization into views: All, High-level, Devtools, Frontend, Backend
- Prompt-driven rules or lightweight classifier for auto-tagging

**Integration options (to decide):**
- Nexus skill invoked by Claude Code
- PostToolUse hook that fires on install commands
- CLAUDE.md instruction telling Claude Code to call `nexus track <thing>`

## Pillar 2: Enrichment Pipeline Overhaul

Current: Gemma generates descriptions from its own knowledge (not capable enough).

**New tiered pipeline (in priority order):**
1. Eagle Mem — session memory may already have context
2. Claude Code context window — the session knows what was just installed and why
3. Context7 — library/framework docs
4. Web search — fallback for non-library concepts
5. Cloud API models (Opus, Sonnet, GPT) — high-quality enrichment when needed
6. Gemma — ONLY for summarization, chat, trivial tasks. Not enrichment.

## Pillar 3: Environment Replication

- `nexus init` in a project creates a project-scoped graph
- `nexus replicate <project>` reads another project's graph and installs all tools/deps/configs
- Smart environment snapshot: not just packages but MCP servers, CLI tools, skills, configs
- One command to bootstrap a new project from a previous one's setup

## Voice Capture (Polyglot)

- "Add [concept] to Nexus" via voice -> Polyglot -> `nexus add`
- Lightweight trigger, not a new architecture

## Open Design Questions

1. Graph scope: one global graph with project tags, or separate DBs per project?
2. Replication granularity: install everything, or pick subsets (e.g., "just frontend tools")?
3. Claude Code integration: skill (user invokes), hook (auto-fires), or CLAUDE.md prompt?
4. Cloud API billing: user's own API keys for Opus/Sonnet/GPT enrichment?
5. Cross-repo portability: how does a Nexus graph travel with a repo (committed file? config?)?

## Not V2 (Later)

- Gap detection ("what should I learn next?")
- Learning journey timeline
- Obsidian import/export
- Cross-platform packaging/signing
