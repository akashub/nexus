import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Concept, ConceptCreate, Conversation, Edge, EdgeCreate, GlobalGraphData, GraphData, Project, Stats } from "../types";

export const API = "http://127.0.0.1:7777/api";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

export function useConcepts(category?: string) {
  const params = category ? `?category=${encodeURIComponent(category)}` : "";
  return useQuery({
    queryKey: ["concepts", category],
    queryFn: () => apiFetch<Concept[]>(`/concepts${params}`),
  });
}

export function useConcept(id: string, refetchInterval?: number | false | ((q: any) => number | false)) {
  return useQuery({
    queryKey: ["concept", id],
    queryFn: () => apiFetch<Concept>(`/concepts/${id}`),
    enabled: !!id,
    refetchInterval: refetchInterval as any,
  });
}

export function useAddConcept() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ConceptCreate) =>
      apiFetch<Concept>("/concepts", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["concepts"] });
      qc.invalidateQueries({ queryKey: ["graph"] });
    },
  });
}

export function useUpdateConcept() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Partial<Concept>) =>
      apiFetch<Concept>(`/concepts/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["concepts"] });
      qc.invalidateQueries({ queryKey: ["concept"] });
      qc.invalidateQueries({ queryKey: ["graph"] });
    },
  });
}

export function useDeleteConcept() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch(`/concepts/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["concepts"] });
      qc.invalidateQueries({ queryKey: ["graph"] });
    },
  });
}

export function useEdges(conceptId: string) {
  return useQuery({
    queryKey: ["edges", conceptId],
    queryFn: () => apiFetch<Edge[]>(`/edges?concept_id=${encodeURIComponent(conceptId)}`),
    enabled: !!conceptId,
  });
}

export function useAddEdge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EdgeCreate) =>
      apiFetch<Edge>("/edges", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["edges"] });
      qc.invalidateQueries({ queryKey: ["graph"] });
    },
  });
}

export function useEnrichConcept() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, mode = "auto" }: { id: string; mode?: string }) =>
      apiFetch<{ status: string }>(`/concepts/${id}/enrich?mode=${mode}`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["concepts"] });
      qc.invalidateQueries({ queryKey: ["concept"] });
      qc.invalidateQueries({ queryKey: ["graph"] });
    },
  });
}

export function useSearch(query: string, semantic = false) {
  const params = `?q=${encodeURIComponent(query)}&semantic=${semantic}`;
  return useQuery({
    queryKey: ["search", query, semantic],
    queryFn: () => apiFetch<Concept[]>(`/search${params}`),
    enabled: query.length > 0,
  });
}

export function useGraph(projectId?: string | null) {
  return useQuery({
    queryKey: ["graph", projectId ?? "all"],
    queryFn: () => apiFetch<GraphData>(`/graph?project_id=${projectId}`),
    enabled: !!projectId,
  });
}

export function useGlobalGraph() {
  return useQuery({
    queryKey: ["graph", "global"],
    queryFn: () => apiFetch<GlobalGraphData>("/graph/global"),
  });
}

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => apiFetch<Project[]>("/projects"),
  });
}

export function useAddProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; path?: string; description?: string }) =>
      apiFetch<Project>("/projects", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["graph", "global"] });
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch("/projects/" + id, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["graph", "global"] });
    },
  });
}

export function useScanProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      apiFetch<{ status: string }>(`/projects/${projectId}/scan`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["graph"] });
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["concepts"] });
    },
  });
}

export function useStats() {
  return useQuery({
    queryKey: ["stats"],
    queryFn: () => apiFetch<Stats>("/stats"),
  });
}

export function useOllamaStatus() {
  return useQuery({ queryKey: ["ai-status"], queryFn: () => apiFetch<{ available: boolean }>("/ai/status"), refetchInterval: 60000, staleTime: 60000 });
}

export function useConversations(limit = 20) {
  return useQuery({
    queryKey: ["conversations", limit],
    queryFn: () => apiFetch<Conversation[]>(`/conversations?limit=${limit}`),
  });
}

export function useRecentConcepts(limit = 8) {
  return useQuery({ queryKey: ["concepts", "recent", limit], queryFn: () => apiFetch<Concept[]>(`/concepts?limit=${limit}`) });
}

export interface ConceptContext { usage_context: string; usage_summary: string; install_commands: string[]; claude_memories: string[]; }

export function useConceptContext(id: string) {
  return useQuery({ queryKey: ["context", id], queryFn: () => apiFetch<ConceptContext>(`/concepts/${id}/context`), enabled: !!id, staleTime: 300000 });
}
