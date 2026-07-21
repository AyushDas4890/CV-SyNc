import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import LogoutBar from "../components/LogoutBar.jsx";

// No backend endpoint for this yet — 07-decisions.md flags "experience" as not part of
// the projects.json contract. This page collects the data and holds it in memory only;
// wire up a real POST once an /api/experience (or similar) endpoint exists.
export default function ExperiencePage() {
  const [entries, setEntries] = useState([]);
  const [form, setForm] = useState({ company: "", role: "", dates: "", bullets: "" });
  const [username, setUsername] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    // reachable directly by URL, so guard it — bounce to login if no session
    api.me()
      .then((res) => setUsername(res.githubUsername))
      .catch(() => navigate("/auth"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function addEntry() {
    if (!form.company && !form.role) return;
    setEntries([...entries, form]);
    setForm({ company: "", role: "", dates: "", bullets: "" });
  }

  function proceed() {
    // TODO: POST entries to backend once endpoint exists. For now just carry on.
    navigate("/onboarding/github");
  }

  return (
    <div className="shell">
      <LogoutBar username={username} />
      <div className="step-indicator">
        <span>1. Account</span>
        <span className="active">2. Experience</span>
        <span>3. GitHub</span>
        <span>4. Template</span>
      </div>
      <h1>Any work experience?</h1>
      <p className="sub">Optional — add internships or jobs, or skip.</p>

      <div className="card">
        <div className="field">
          <label>Company</label>
          <input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
        </div>
        <div className="field">
          <label>Role</label>
          <input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
        </div>
        <div className="field">
          <label>Dates</label>
          <input value={form.dates} onChange={(e) => setForm({ ...form, dates: e.target.value })} placeholder="Jun 2025 – Aug 2025" />
        </div>
        <div className="field">
          <label>Bullets</label>
          <textarea rows={3} value={form.bullets} onChange={(e) => setForm({ ...form, bullets: e.target.value })} />
        </div>
        <button className="secondary" type="button" onClick={addEntry}>Add entry</button>
      </div>

      {entries.length > 0 && (
        <div className="card">
          {entries.map((en, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <strong>{en.role}</strong> @ {en.company} ({en.dates})
            </div>
          ))}
        </div>
      )}

      <div className="row">
        <button className="primary" onClick={proceed}>Continue</button>
        <button className="ghost" onClick={proceed}>Skip</button>
      </div>
    </div>
  );
}
