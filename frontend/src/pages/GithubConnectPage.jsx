import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import LogoutBar from "../components/LogoutBar.jsx";

// Login already happened via GitHub OAuth (AuthPage). This page is now just
// the repo picker — no separate "Connect GitHub" step, that button is gone.
export default function GithubConnectPage() {
  const [repos, setRepos] = useState(null); // null = loading
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
      const me = await api.me(); // confirms session is real; throws 401 if not logged in
      setUsername(me.githubUsername);
      const res = await api.githubRepos();
      setRepos(res.repos || []);
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

  return (
    <div className="shell">
      <LogoutBar username={username} />
      <div className="step-indicator">
        <span>1. Account</span>
        <span>2. Experience</span>
        <span className="active">3. GitHub</span>
        <span>4. Template</span>
      </div>
      <h1>Pick your repos</h1>
      <p className="sub">Choose which repos go on your CV.</p>

      {error && <p className="error">{error}</p>}
      {repos === null && <p className="notice">loading repos…</p>}

      {repos !== null && (
        <div className="card">
          <div className="repo-list">
            {repos.map((r) => (
              <label key={r.id} className="repo-item">
                <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggle(r.id)} />
                <div>
                  <div className="name">{r.name}</div>
                  <div className="meta">{r.language || "—"} · ★ {r.stars} · {r.description || "no description"}</div>
                </div>
              </label>
            ))}
            {repos.length === 0 && <p className="notice">no public repos found</p>}
          </div>
        </div>
      )}

      <div className="row">
        <button className="primary" disabled={!repos || selected.size === 0} onClick={() => navigate("/onboarding/templates")}>
          Continue ({selected.size} selected)
        </button>
      </div>
    </div>
  );
}
