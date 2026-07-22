import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import LogoutBar from "../components/LogoutBar.jsx";
import "../styles.css";

export default function GithubConnectPage() {
  const [repos, setRepos] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [error, setError] = useState("");
  const [username, setUsername] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function load() {
    try {
      const me = await api.me();
      setUsername(me.githubUsername);
      const res = await api.githubRepos();
      const fetched = res.repos || [];
      setRepos(fetched);

      // Re-select whatever was previously chosen (by id), now that we have the full list
      try {
        const saved = JSON.parse(localStorage.getItem("cv_sync_selected_repos") || "[]");
        const savedIds = new Set(saved.map((r) => r.id));
        if (savedIds.size > 0) setSelected(savedIds);
      } catch {
        // ignore malformed cache
      }
    } catch (err) {
      if (err.message.includes("401")) {
        navigate("/auth");
        return;
      }
      setError(err.message);
      setRepos([]);
    }
  }

  function toggle(id) {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  }

  function proceed() {
    const selectedRepos = (repos || []).filter((r) => selected.has(r.id));
    localStorage.setItem("cv_sync_selected_repos", JSON.stringify(selectedRepos));
    navigate("/onboarding/templates");
  }

  return (
    <div className="page-root">
      <LogoutBar username={username} />

      <div className="page-content">
        {/* Step indicator */}
        <div className="step-indicator">
          <div className="step-item done">
            <div className="step-dot">✓</div>
            <span>Account</span>
          </div>
          <div className="step-connector" />
          <div className="step-item done">
            <div className="step-dot">✓</div>
            <span>Profile</span>
          </div>
          <div className="step-connector" />
          <div className="step-item done">
            <div className="step-dot">✓</div>
            <span>Experience</span>
          </div>
          <div className="step-connector" />
          <div className="step-item active">
            <div className="step-dot">4</div>
            <span>GitHub</span>
          </div>
          <div className="step-connector" />
          <div className="step-item">
            <div className="step-dot">5</div>
            <span>Template</span>
          </div>
        </div>

        {/* Heading */}
        <div className="page-heading">
          <h1>Pick your repos</h1>
          <p className="sub">Choose which repositories to feature on your CV.</p>
        </div>

        {error && <p className="error" style={{ marginTop: 16 }}>{error}</p>}

        {repos === null && (
          <p className="notice" style={{ marginTop: 24, textAlign: "center" }}>
            ⏳ loading your repositories…
          </p>
        )}

        {repos !== null && (
          <div className="card">
            {repos.length === 0 ? (
              <p className="notice">No public repos found on your account.</p>
            ) : (
              <div className="repo-list">
                {repos.map((r) => (
                  <label key={r.id} className="repo-item">
                    <input
                      type="checkbox"
                      checked={selected.has(r.id)}
                      onChange={() => toggle(r.id)}
                    />
                    <div>
                      <div className="name">{r.name}</div>
                      <div className="meta">
                        {r.language || "—"} · ★ {r.stars}
                        {r.description ? ` · ${r.description}` : ""}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Selection summary */}
        {selected.size > 0 && (
          <p className="notice" style={{ marginTop: 12 }}>
            {selected.size} repo{selected.size !== 1 ? "s" : ""} selected
          </p>
        )}

        {/* Navigation */}
        <div className="row">
          <button
            className="primary"
            disabled={!repos || selected.size === 0}
            onClick={proceed}
          >
            Continue ({selected.size} selected)
          </button>
        </div>
      </div>
    </div>
  );
}
