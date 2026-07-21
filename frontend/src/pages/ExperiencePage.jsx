import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import LogoutBar from "../components/LogoutBar.jsx";
import "../styles.css";

export default function ExperiencePage() {
  const [entries, setEntries] = useState([]);
  const [form, setForm] = useState({ company: "", role: "", dates: "", bullets: "" });
  const [username, setUsername] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
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
    navigate("/onboarding/github");
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
          <div className="step-item active">
            <div className="step-dot">2</div>
            <span>Experience</span>
          </div>
          <div className="step-connector" />
          <div className="step-item">
            <div className="step-dot">3</div>
            <span>GitHub</span>
          </div>
          <div className="step-connector" />
          <div className="step-item">
            <div className="step-dot">4</div>
            <span>Template</span>
          </div>
        </div>

        {/* Heading */}
        <div className="page-heading">
          <h1>Any work experience?</h1>
          <p className="sub">Optional — add internships or jobs, or skip ahead.</p>
        </div>

        {/* Form card */}
        <div className="card">
          <div className="field">
            <label>Company</label>
            <input
              placeholder="e.g. Google, Accenture"
              value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Role</label>
            <input
              placeholder="e.g. Software Engineer Intern"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Dates</label>
            <input
              value={form.dates}
              onChange={(e) => setForm({ ...form, dates: e.target.value })}
              placeholder="Jun 2025 – Aug 2025"
            />
          </div>
          <div className="field">
            <label>Bullet points</label>
            <textarea
              rows={3}
              value={form.bullets}
              onChange={(e) => setForm({ ...form, bullets: e.target.value })}
              placeholder="Key accomplishments, technologies used…"
            />
          </div>
          <button className="secondary" type="button" onClick={addEntry}>
            + Add entry
          </button>
        </div>

        {/* Saved entries */}
        {entries.length > 0 && (
          <div className="card">
            {entries.map((en, i) => (
              <div key={i} className="entry-item">
                <strong>{en.role}</strong>
                <div className="entry-meta">{en.company}{en.dates ? ` · ${en.dates}` : ""}</div>
              </div>
            ))}
          </div>
        )}

        {/* Navigation */}
        <div className="row">
          <button className="primary" onClick={proceed}>Continue</button>
          <button className="ghost" onClick={proceed}>Skip for now</button>
        </div>
      </div>
    </div>
  );
}
