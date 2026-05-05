import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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

export function useScanStatus(projectId: string | null) {
  return useQuery({
    queryKey: ["scan-status", projectId],
    queryFn: () => apiFetch<{ status: string | null }>(`/projects/${projectId}/scan-status`),
    enabled: !!projectId,
    refetchInterval: (q) => q.state.data?.status ? 1000 : false,
  });
}

export interface AiModels {
  ollama: { available: boolean; models: string[] };
  cloud: Array<{ provider: string; model: string; via?: string; configured: boolean }>;
}

export function useAiModels() {
  return useQuery({
    queryKey: ["ai-models"],
    queryFn: () => apiFetch<AiModels>("/ai/models"),
    staleTime: 60000,
  });
}

export function useAiConfig() {
  return useQuery({
    queryKey: ["ai-config"],
    queryFn: () => apiFetch<Record<string, Record<string, string>>>("/ai/config"),
    staleTime: 30000,
  });
}

export function useSaveAiConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { provider: string; settings: Record<string, string> }) =>
      apiFetch<{ status: string }>(`/ai/config/${args.provider}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(args.settings),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-config"] });
      qc.invalidateQueries({ queryKey: ["ai-models"] });
    },
  });
}
