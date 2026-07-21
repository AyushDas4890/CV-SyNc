import { api } from "../api.js";

// GitHub OAuth IS the login (Ayush: skip Google, GitHub-only for V1).
// Clicking through leaves the SPA entirely — GitHub's consent screen needs a
// real top-level navigation, not a fetch — then the backend redirects back here.
export default function AuthPage() {
  function loginWithGithub() {
    window.location.href = api.githubLoginUrl();
  }

  return (
    <div className="shell">
      <div className="step-indicator">
        <span className="active">1. Account</span>
        <span>2. Experience</span>
        <span>3. GitHub</span>
        <span>4. Template</span>
      </div>
      <h1>Sign in to CV-Sync</h1>
      <p className="sub">GitHub is your account — no separate password.</p>

      <div className="card">
        <button className="primary" onClick={loginWithGithub}>
          Continue with GitHub
        </button>
      </div>
    </div>
  );
}
