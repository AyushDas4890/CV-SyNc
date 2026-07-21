import { Routes, Route, Navigate } from "react-router-dom";
import AuthPage from "./pages/AuthPage.jsx";
import ExperiencePage from "./pages/ExperiencePage.jsx";
import GithubConnectPage from "./pages/GithubConnectPage.jsx";
import TemplatePage from "./pages/TemplatePage.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/auth" replace />} />
      <Route path="/auth" element={<AuthPage />} />
      <Route path="/onboarding/experience" element={<ExperiencePage />} />
      <Route path="/onboarding/github" element={<GithubConnectPage />} />
      <Route path="/onboarding/templates" element={<TemplatePage />} />
    </Routes>
  );
}
