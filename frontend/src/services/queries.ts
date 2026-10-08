import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useCurrentUser } from "@/features/auth/authState";
import type {
  NewContestationInput,
  NewDecisionInput,
  NewEvidenceReviewInput,
  NewRuleDecisionInput,
  NewProjectInput,
  ProjectQuery,
} from "@/domain/types";
import {
  requestReanalysis,
  createContestation,
  createEvidenceReview,
  createProject,
  createRuleDecision,
  getAnalyses,
  getProject,
  listContestations,
  listDecisions,
  listEvidenceReviews,
  listProjects,
  listRuleDecisions,
  saveDecision,
} from "@/services/api";

const PROCESSING_POLL_MS = 2000;

export const queryKeys = {
  projects: ["projects"] as const,
  project: (projectId: string) => ["projects", projectId] as const,
  analyses: (projectId: string) => ["projects", projectId, "analyses"] as const,
  decisions: (projectId: string) =>
    ["projects", projectId, "decisions"] as const,
  contestations: (projectId: string) =>
    ["projects", projectId, "contestations"] as const,
  ruleDecisions: (projectId: string) => ["projects", projectId, "rule-decisions"] as const,
  evidenceReviews: (projectId: string) => ["projects", projectId, "evidence-reviews"] as const,
};

/** A project sent minutes ago may still finish processing: worth polling */
const RECENT_MS = 10 * 60 * 1000;

export const useProjects = (query: ProjectQuery) =>
  useQuery({
    queryKey: [...queryKeys.projects, "list", query],
    queryFn: () => listProjects(query),
    // Keep the current page on screen while the next one loads
    placeholderData: keepPreviousData,
    refetchInterval: (q) =>
      q.state.data?.items.some(
        (p) => p.status === "processing" && Date.now() - Date.parse(p.createdAt) < RECENT_MS,
      )
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

/** All analyses of a project (one per method); null while processing */
export const useAnalyses = (projectId: string) =>
  useQuery({
    queryKey: queryKeys.analyses(projectId),
    queryFn: () => getAnalyses(projectId),
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
  const user = useCurrentUser();
  return useMutation({
    mutationFn: (input: NewProjectInput) => createProject(input, user.id),
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

export const useContestations = (projectId: string) =>
  useQuery({
    queryKey: queryKeys.contestations(projectId),
    queryFn: () => listContestations(projectId),
  });

export const useCreateContestation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: NewContestationInput) => createContestation(input),
    onSuccess: (contestation) =>
      queryClient.invalidateQueries({
        queryKey: queryKeys.contestations(contestation.projectId),
      }),
  });
};

/** Reanalysis changes the contestation and, if accepted, the analysis and the list */
export const useRequestReanalysis = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (contestationId: string) => requestReanalysis(contestationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.projects }),
  });
};

export const useRuleDecisions = (projectId: string) =>
  useQuery({
    queryKey: queryKeys.ruleDecisions(projectId),
    queryFn: () => listRuleDecisions(projectId),
  });

export const useCreateRuleDecision = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: NewRuleDecisionInput) => createRuleDecision(input),
    onSuccess: (decision) =>
      queryClient.invalidateQueries({ queryKey: queryKeys.ruleDecisions(decision.projectId) }),
  });
};

export const useEvidenceReviews = (projectId: string) =>
  useQuery({
    queryKey: queryKeys.evidenceReviews(projectId),
    queryFn: () => listEvidenceReviews(projectId),
  });

export const useCreateEvidenceReview = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: NewEvidenceReviewInput) => createEvidenceReview(input),
    onSuccess: (review) =>
      queryClient.invalidateQueries({ queryKey: queryKeys.evidenceReviews(review.projectId) }),
  });
};
