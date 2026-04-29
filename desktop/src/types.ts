export interface Concept {
  id: string;
  name: string;
  description: string | null;
  summary: string | null;
  category: string | null;
  tags: string[];
  source: string;
  notes: string | null;
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

export interface Stats {
  concept_count: number;
  edge_count: number;
  categories: Record<string, number>;
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
