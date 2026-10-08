import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import { AppProviders } from "@/providers/AppProviders";
import { AppRouter } from "@/routes/AppRouter";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppProviders>
      <AppRouter />
    </AppProviders>
  </StrictMode>,
);
