import { useParams } from "react-router-dom";

export const DecisionPage = () => {
  const { projectId } = useParams();

  return (
    <div className="mx-auto w-full max-w-3xl p-6">
      <h1 className="text-2xl font-semibold">Decisão</h1>
      <p className="text-fg-muted">Projeto {projectId}</p>
    </div>
  );
};
