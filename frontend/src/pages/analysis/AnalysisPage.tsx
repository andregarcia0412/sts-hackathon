import { useParams } from "react-router-dom";

export const AnalysisPage = () => {
  const { projectId } = useParams();

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold">Análise</h1>
      <p className="text-fg-muted">Projeto {projectId}</p>
    </div>
  );
};
