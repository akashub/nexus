import { useQuery } from "@tanstack/react-query";
import type { Concept, Conversation } from "../types";
import { apiFetch } from "./useApi";

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

export interface JourneyWeek {
  week: string;
  week_start: string;
  concepts: Array<{ id: string; name: string; category: string | null; summary: string | null; description: string | null }>;
}

export function useJourney(projectId?: string | null, days = 90) {
  const params = new URLSearchParams({ days: String(days) });
  if (projectId) params.set("project_id", projectId);
  return useQuery({
    queryKey: ["journey", projectId ?? "all", days],
    queryFn: () => apiFetch<JourneyWeek[]>(`/journey?${params}`),
  });
}

export interface GapResult {
  category: string;
  reason: string;
  have: string[];
  missing_type: string;
  suggestions: string[];
}

export function useGaps(projectId: string) {
  return useQuery({
    queryKey: ["gaps", projectId],
    queryFn: () => apiFetch<GapResult[]>(`/projects/${projectId}/gaps`),
    enabled: !!projectId,
  });
}

export interface VersionInfo {
  current: string;
  latest: string;
  update_available: boolean;
  assets?: { macos_arm?: string; macos_x64?: string; windows?: string; linux?: string };
  release_url?: string;
}

export function useVersionCheck() {
  return useQuery({
    queryKey: ["version"],
    queryFn: () => apiFetch<VersionInfo>("/version"),
    staleTime: 3600000,
    refetchOnWindowFocus: false,
  });
}
