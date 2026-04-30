export interface Project {
  id: string;
  name: string;
  path: string | null;
  description: string | null;
  last_scanned_at: string | null;
  concept_count?: number;
  created_at: string;
  updated_at: string;
}

export interface Concept {
  id: string;
  name: string;
  description: string | null;
  summary: string | null;
  category: string | null;
  tags: string[];
  source: string;
  notes: string | null;
  quickstart: string | null;
  doc_url: string | null;
  context7_id: string | null;
  enrich_status: string | null;
  project_id: string | null;
  semantic_group: string | null;
  setup_commands: string[];
  config_files: { path: string; content: string }[];
  created_at: string;
  updated_at: string;
}

export interface Edge {
  id: string;
  source_id: string;
  target_id: string;
  relationship: string;
  description: string | null;
  weight: number;
  created_at: string;
}

export interface GraphData {
  nodes: Concept[];
  edges: Edge[];
}

export interface GlobalGraphData {
  nodes: (Project & { concept_count: number })[];
  edges: { source_id: string; target_id: string; weight: number; relationship: string }[];
  unassigned_count: number;
}

export interface Stats {
  concept_count: number;
  edge_count: number;
  categories: Record<string, number>;
  project_count: number;
}

export interface Conversation {
  id: string;
  question: string;
  answer: string;
  created_at: string;
}

export interface ConceptCreate {
  name: string;
  category?: string;
  tags?: string[];
  notes?: string;
  no_enrich?: boolean;
  project_id?: string;
}

export interface EdgeCreate {
  source_id: string;
  target_id: string;
  relationship?: string;
  description?: string;
}

export function slugify(name: string): string {
  return name.toLowerCase().replace(/\s+/g, "_");
}
