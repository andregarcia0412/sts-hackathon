import { Outlet, useParams } from "react-router-dom";
import { AssistantProvider } from "@/features/assistant/AssistantProvider";
import { AssistantWidget } from "@/features/assistant/AssistantWidget";

/** Screens of one project (analysis, decision) share the assistant conversation */
export const ProjectLayout = () => {
  const { projectId } = useParams();

  return (
    <AssistantProvider key={projectId}>
      <Outlet />
      <AssistantWidget />
    </AssistantProvider>
  );
};
