import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { AnalysisPage } from "@/pages/analysis/AnalysisPage";
import { DecisionPage } from "@/pages/decision/DecisionPage";
import { NotFoundPage } from "@/pages/not-found/NotFoundPage";
import { ProjectsPage } from "@/pages/projects/ProjectsPage";

export const AppRouter = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/projetos" replace />} />
          <Route path="projetos" element={<ProjectsPage />} />
          <Route
            path="projetos/:projectId/analise"
            element={<AnalysisPage />}
          />
          <Route
            path="projetos/:projectId/decisao"
            element={<DecisionPage />}
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};
