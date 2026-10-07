export const SELECTED_NODE_PARAM = "no";

export const paths = {
  projects: () => "/projetos",
  analysis: (projectId: string, nodeId?: string) =>
    nodeId
      ? `/projetos/${projectId}/analise?${SELECTED_NODE_PARAM}=${encodeURIComponent(nodeId)}`
      : `/projetos/${projectId}/analise`,
  decision: (projectId: string) => `/projetos/${projectId}/decisao`,
};
