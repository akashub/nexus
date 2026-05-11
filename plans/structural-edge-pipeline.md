# Structural Edge Pipeline — Implementation Plan

## Objective
Replace similarity-based edge creation with structural scanning + LLM gap-fill. Clean + rebuild all edges.

## Acceptance Criteria
- Zero cross-project edges
- MCP in Farmerchat has edges
- eagle-* concepts in environment layer, not project graph
- Every structural edge traces to a config file
- Bulk enrich runs the full pipeline
- Context display shows AI summary, not raw dumps

## Phase 1: Schema Migration
- Add `confidence` column to edges (default "structural")
- Add `layer` column to concepts (default "project")
- Backfill existing edges as "inferred"
- Backfill environment-layer concepts by source pattern

## Phase 2: Structural Scanners
- Upgrade packages.py to produce ScannedRelationship edges with confidence
- Upgrade claude_md.py to extract relationships from Stack section
- Upgrade mcp.py to create uses edges
- New: import scanner (levels 0/1/2)

## Phase 3: Similarity + LLM Gap-Fill
- New similarity pass: same-category + >0.7 + similar_to only
- New LLM gap-fill: orphan concepts + full CLAUDE.md context
- Replace old infer.py

## Phase 4: Pipeline Orchestration
- New rebuild_project_edges() function
- Wire into bulk enrich, scan, hooks, MCP, CLI
- Delete old _suggest_connections

## Phase 5: Context Cleanup
- Filter noise in context.py
- Add usage_summary field to concepts
- Frontend: summary + expandable raw

## Phase 6: Frontend Layer Toggle
- Add layer filter to sidebar
- Default to project layer only
- Pass to GraphView

## Phase 7: Clean + Rebuild + Validate
- Delete all existing edges
- Run pipeline on all 4 projects
- Verify against benchmark
