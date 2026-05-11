-- Add confidence level to edges: structural, similarity, inferred, manual
ALTER TABLE edges ADD COLUMN confidence TEXT DEFAULT 'structural';

-- Backfill existing edges as inferred (they came from the old similarity system)
UPDATE edges SET confidence = 'inferred';

-- Add layer to concepts: project vs environment
ALTER TABLE concepts ADD COLUMN layer TEXT DEFAULT 'project';

-- Backfill environment layer for known dev-tool patterns
UPDATE concepts SET layer = 'environment'
WHERE source IN ('eagle_mem')
AND (
    name LIKE 'eagle-%'
    OR name LIKE 'claude-plugins%'
    OR name IN ('cursor', 'llm-wiki', 'copilot')
);

-- Add usage_summary for context display cleanup
ALTER TABLE concepts ADD COLUMN usage_summary TEXT;
