import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { ProjectLayout } from "@/components/layout/ProjectLayout";
import { RequireAuth } from "@/features/auth/AuthProvider";
import { LoginPage } from "@/pages/login/LoginPage";
import { AnalysisPage } from "@/pages/analysis/AnalysisPage";
import { DecisionPage } from "@/pages/decision/DecisionPage";
import { NotFoundPage } from "@/pages/not-found/NotFoundPage";
import { NewProjectPage } from "@/pages/projects/NewProjectPage";
import { ProjectsPage } from "@/pages/projects/ProjectsPage";

export const AppRouter = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="login" element={<LoginPage />} />
        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/projetos" replace />} />
          <Route path="projetos" element={<ProjectsPage />} />
          <Route path="projetos/novo" element={<NewProjectPage />} />
          <Route path="projetos/:projectId" element={<ProjectLayout />}>
            <Route index element={<Navigate to="analise" replace />} />
            <Route path="analise" element={<AnalysisPage />} />
            <Route path="decisao" element={<DecisionPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};
