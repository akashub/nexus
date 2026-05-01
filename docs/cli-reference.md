# CLI Reference

Full reference for all `nexus` commands.

## Core

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

## Projects

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

## AI

```
nexus enrich-relationships    Infer edges between concepts using embeddings + AI
nexus cluster                 Assign semantic groups to concepts using AI
```

## Integration

```
nexus mcp install             Install MCP server, hooks, and skill into Claude Code
nexus mcp install --check     Check installation status
nexus mcp install --uninstall Remove Nexus from Claude Code
nexus mcp serve               Start the MCP server (used by Claude Code, not run manually)

nexus ingest <file.jsonl>     Import a knowledge ledger file
nexus track <name>            Track a package install
  --source                    npm | pip | brew | cargo
```

## System

```
nexus status                  Show full integration status
nexus serve                   Start the API server (for desktop app)
  --port                      Default: 7777
  --host                      Default: 127.0.0.1
nexus db init                 Initialize / migrate the database
```
