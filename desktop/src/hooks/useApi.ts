import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  AskResponse,
  Concept,
  ConceptCreate,
  Edge,
  EdgeCreate,
  GraphData,
  Stats,
} from "../types";

const API = "http://127.0.0.1:7777/api";

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
  const params = category ? `?category=${category}` : "";
  return useQuery({
    queryKey: ["concepts", category],
    queryFn: () => apiFetch<Concept[]>(`/concepts${params}`),
  });
}

export function useConcept(id: string) {
  return useQuery({
    queryKey: ["concept", id],
    queryFn: () => apiFetch<Concept>(`/concepts/${id}`),
    enabled: !!id,
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
    queryFn: () => apiFetch<Edge[]>(`/edges?concept_id=${conceptId}`),
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
    mutationFn: (id: string) =>
      apiFetch<{ status: string }>(`/concepts/${id}/enrich`, { method: "POST" }),
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

export function useAsk() {
  return useMutation({
    mutationFn: (question: string) =>
      apiFetch<AskResponse>("/ask", {
        method: "POST",
        body: JSON.stringify({ question }),
      }),
  });
}

export function useGraph() {
  return useQuery({
    queryKey: ["graph"],
    queryFn: () => apiFetch<GraphData>("/graph"),
  });
}

export function useStats() {
  return useQuery({
    queryKey: ["stats"],
    queryFn: () => apiFetch<Stats>("/stats"),
  });
}

export function useOllamaStatus() {
  return useQuery({
    queryKey: ["ai-status"],
    queryFn: () => apiFetch<{ available: boolean }>("/ai/status"),
    refetchInterval: 60000,
    staleTime: 60000,
  });
}

export function useRecentConcepts(limit = 8) {
  return useQuery({
    queryKey: ["concepts", "recent", limit],
    queryFn: () => apiFetch<Concept[]>(`/concepts?limit=${limit}`),
  });
}
