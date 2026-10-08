import { Link } from "react-router-dom";
import { paths } from "@/routes/paths";

export const NotFoundPage = () => {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
      <p className="text-sm font-medium text-fg-muted">Erro 404</p>
      <h1 className="text-2xl font-semibold">Página não encontrada</h1>
      <p className="text-fg-muted">
        O endereço acessado não existe ou foi movido.
      </p>
      <Link
        to={paths.projects()}
        className="btn-primary mt-2"
      >
        Voltar para os projetos
      </Link>
    </div>
  );
};
