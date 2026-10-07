import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { NewDecisionInput, NewProjectInput } from "@/domain/types";
import {
  createProject,
  getAnalysis,
  getProject,
  listDecisions,
  listProjects,
  saveDecision,
} from "@/services/api";

const PROCESSING_POLL_MS = 2000;

export const queryKeys = {
  projects: ["projects"] as const,
  project: (projectId: string) => ["projects", projectId] as const,
  analysis: (projectId: string) => ["projects", projectId, "analysis"] as const,
  decisions: (projectId: string) =>
    ["projects", projectId, "decisions"] as const,
};

export const useProjects = () =>
  useQuery({
    queryKey: queryKeys.projects,
    queryFn: listProjects,
    // Keep polling while something is still being processed
    refetchInterval: (query) =>
      query.state.data?.some((p) => p.status === "processing")
        ? PROCESSING_POLL_MS
        : false,
  });

export const useProject = (projectId: string) =>
  useQuery({
    queryKey: queryKeys.project(projectId),
    queryFn: () => getProject(projectId),
    refetchInterval: (query) =>
      query.state.data?.status === "processing" ? PROCESSING_POLL_MS : false,
  });

export const useAnalysis = (projectId: string) =>
  useQuery({
    queryKey: queryKeys.analysis(projectId),
    queryFn: () => getAnalysis(projectId),
    refetchInterval: (query) =>
      query.state.data === null ? PROCESSING_POLL_MS : false,
  });

export const useDecisions = (projectId: string) =>
  useQuery({
    queryKey: queryKeys.decisions(projectId),
    queryFn: () => listDecisions(projectId),
  });

export const useCreateProject = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: NewProjectInput) => createProject(input),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.projects }),
  });
};

export const useSaveDecision = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: NewDecisionInput) => saveDecision(input),
    // Prefix match: refreshes the list, the project and its decisions
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.projects }),
  });
};
