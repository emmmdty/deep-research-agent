import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { SessionGuard } from "./components/SessionGuard";
import { AdminModelsPage } from "./features/admin/AdminModelsPage";
import { AdminRuntimePage } from "./features/admin/AdminRuntimePage";
import { LoginPage } from "./features/admin/LoginPage";
import { MemoryPage } from "./features/memory/MemoryPage";
import { RunWorkspace } from "./features/report/RunWorkspace";
import { TopicsIndex } from "./features/workspace/TopicsIndex";
import { TopicOverview, TopicWorkspace } from "./features/workspace/TopicWorkspace";

export function AppRouter() {
  return <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route element={<SessionGuard />}>
      <Route element={<AppShell />}>
      <Route path="/topics" element={<TopicsIndex />} />
      <Route path="/topics/:topicId" element={<TopicWorkspace />}>
        <Route index element={<TopicOverview />} />
        <Route path="runs/:runId" element={<RunWorkspace />} />
      </Route>
      <Route path="/memory" element={<MemoryPage />} />
      <Route path="/admin/models" element={<AdminModelsPage />} />
      <Route path="/admin/runtime" element={<AdminRuntimePage />} />
      </Route>
    </Route>
    <Route path="*" element={<Navigate replace to="/topics" />} />
  </Routes>;
}
