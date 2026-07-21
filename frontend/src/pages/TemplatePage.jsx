import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import LogoutBar from "../components/LogoutBar.jsx";

// Placeholder thumbnails — real images from IamAbhinav01/CV_TEMPLATES not provided yet
// (Ayush said he'd send them). No backend endpoint to list/save templates either.
const TEMPLATES = [
  { id: "jake", name: "Jake Gutierrez (current)" },
  { id: "template-2", name: "Template 2 — placeholder" },
  { id: "template-3", name: "Template 3 — placeholder" },
  { id: "template-4", name: "Template 4 — placeholder" },
];

export default function TemplatePage() {
  const [selected, setSelected] = useState("jake");
  const [username, setUsername] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    // reachable directly by URL, so guard it — bounce to login if no session
    api.me()
      .then((res) => setUsername(res.githubUsername))
      .catch(() => navigate("/auth"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="shell">
      <LogoutBar username={username} />
      <div className="step-indicator">
        <span>1. Account</span>
        <span>2. Experience</span>
        <span>3. GitHub</span>
        <span className="active">4. Template</span>
      </div>
      <h1>Choose a CV template</h1>
      <p className="sub notice">placeholder thumbnails — swap in real images from CV_TEMPLATES when available</p>

      <div className="template-grid">
        {TEMPLATES.map((t) => (
          <div
            key={t.id}
            className={`template-card ${selected === t.id ? "selected" : ""}`}
            onClick={() => setSelected(t.id)}
          >
            <div className="thumb">preview</div>
            <div className="label">{t.name}</div>
          </div>
        ))}
      </div>

      <button className="primary" disabled>
        Finish (writer service not built yet)
      </button>
    </div>
  );
}
