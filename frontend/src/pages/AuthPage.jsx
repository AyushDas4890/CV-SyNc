import { useState } from "react";
import { api } from "../api.js";
import "./AuthPage.css";

export default function AuthPage() {
  const [showEmail, setShowEmail] = useState(false);
  const [emailMode, setEmailMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [emailError, setEmailError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  function loginWithGithub() {
    window.location.href = api.githubLoginUrl();
  }


  async function handleEmailSubmit(e) {
    e.preventDefault();
    setEmailError("");
    if (!email || !password) {
      setEmailError("Please fill in all fields.");
      return;
    }
    setIsLoading(true);
    try {
      if (emailMode === "register") {
        await api.emailRegister(email, password, displayName);
      } else {
        await api.emailLogin(email, password);
      }
      // Session cookie set by backend — navigate to app
      window.location.href = "/";
    } catch (err) {
      setEmailError(err.message || "Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="auth-root">
      {/* Background grid pattern */}
      <div className="auth-grid" />

      {/* Left — Branding Panel */}
      <div className="auth-left">
        <div className="auth-brand">
          <div className="auth-logo">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <rect width="40" height="40" rx="10" fill="#1A2E4A" />
              <path d="M8 28 L20 12 L32 28" stroke="#F59E0B" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
              <path d="M14 22 L26 22" stroke="#F59E0B" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
          </div>
          <span className="auth-brand-name">CV-Sync</span>
        </div>

        <div className="auth-hero">
          <h1 className="auth-headline">
            Your GitHub.<br />
            <span className="auth-highlight">Your resume, synced.</span>
          </h1>
          <p className="auth-tagline">
            CV-Sync scans your repositories, writes AI-powered resume bullets, and compiles a pixel-perfect LaTeX PDF — with you in control at every step.
          </p>
        </div>

        <ul className="auth-features">
          <li>
            <span className="auth-feature-icon">⚡</span>
            <span>Instant repo scanning & AI bullet generation</span>
          </li>
          <li>
            <span className="auth-feature-icon">🎨</span>
            <span>8 professional LaTeX templates</span>
          </li>
          <li>
            <span className="auth-feature-icon">🔒</span>
            <span>Human-in-the-loop approval before every PDF</span>
          </li>
          <li>
            <span className="auth-feature-icon">🚀</span>
            <span>One-click compile to publication-ready PDF</span>
          </li>
        </ul>
      </div>

      {/* Right — Sign-in Panel */}
      <div className="auth-right">
        <div className="auth-card">
          <div className="auth-card-header">
            <h2 className="auth-card-title">Get started</h2>
            <p className="auth-card-sub">Sign in with GitHub — no separate password needed.</p>
          </div>

          {/* ── GitHub (Primary) ── */}
          <button className="auth-github-btn" onClick={loginWithGithub}>
            <svg className="auth-github-icon" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
            </svg>
            Continue with GitHub
            <span className="auth-badge">Recommended</span>
          </button>

          <div className="auth-divider"><span>or</span></div>

          {/* ── Email / Password ── */}
          {!showEmail ? (
            <button
              className="auth-email-btn"
              onClick={() => { setShowEmail(true); setEmailMode("login"); setEmailError(""); }}
            >
              <svg className="auth-email-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="4" width="20" height="16" rx="2"/>
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
              </svg>
              Sign in with Email
            </button>
          ) : (
            <form className="auth-email-form" onSubmit={handleEmailSubmit}>
              <div className="auth-email-tabs">
                <button
                  type="button"
                  className={`auth-tab ${emailMode === "login" ? "active" : ""}`}
                  onClick={() => { setEmailMode("login"); setEmailError(""); }}
                >Sign In</button>
                <button
                  type="button"
                  className={`auth-tab ${emailMode === "register" ? "active" : ""}`}
                  onClick={() => { setEmailMode("register"); setEmailError(""); }}
                >Create Account</button>
              </div>
              {emailMode === "register" && (
                <input
                  id="auth-display-name"
                  type="text"
                  placeholder="Display name (optional)"
                  value={displayName}
                  onChange={e => setDisplayName(e.target.value)}
                  autoComplete="name"
                />
              )}
              <input
                id="auth-email"
                type="email"
                placeholder="Email address"
                value={email}
                onChange={e => setEmail(e.target.value)}
                autoFocus
                autoComplete="email"
              />
              <input
                id="auth-password"
                type="password"
                placeholder={emailMode === "register" ? "Password (min 8 chars)" : "Password"}
                value={password}
                onChange={e => setPassword(e.target.value)}
                autoComplete={emailMode === "register" ? "new-password" : "current-password"}
              />
              {emailError && <p className="auth-email-error">{emailError}</p>}
              <div className="auth-email-actions">
                <button type="submit" className="auth-email-submit" disabled={isLoading}>
                  {isLoading ? "Please wait…" : emailMode === "register" ? "Create Account" : "Sign In"}
                </button>
                <button type="button" className="auth-email-cancel" onClick={() => { setShowEmail(false); setEmailError(""); }}>Cancel</button>
              </div>
              {emailMode === "login" && (
                <p className="auth-email-forgot"><a href="#">Forgot password?</a></p>
              )}
            </form>
          )}

          <p className="auth-privacy" style={{marginTop: '20px'}}>
            GitHub users: we only access your <strong>public repositories</strong>. No private repo access, ever.
          </p>
        </div>

        <p className="auth-footer">
          By continuing, you agree to CV-Sync's usage of the GitHub OAuth app for authentication.
        </p>
      </div>
    </div>
  );
}
