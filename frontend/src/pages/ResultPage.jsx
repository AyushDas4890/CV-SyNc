import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import LogoutBar from "../components/LogoutBar.jsx";
import { api } from "../api.js";
import "../styles.css";

// Shows the LaTeX CV_BRAIN generated, and compiles it to a PDF via CV_BUILDER's
// /api/compile.
export default function ResultPage() {
  const [username, setUsername] = useState("");
  const [result, setResult] = useState(null);
  const [copied, setCopied] = useState(false);
  const [compiling, setCompiling] = useState(false);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [compileError, setCompileError] = useState(null); // { message, log, errors }
  const navigate = useNavigate();

  useEffect(() => {
    api.me()
      .then((res) => setUsername(res.githubUsername))
      .catch(() => navigate("/auth"));

    const cached = localStorage.getItem("cv_sync_generated_cv");
    if (!cached) {
      navigate("/onboarding/templates");
      return;
    }
    setResult(JSON.parse(cached));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Revoke the blob URL when it's replaced or the page unmounts
  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
  }, [pdfUrl]);

  function copyTex() {
    if (!result?.tex) return;
    navigator.clipboard.writeText(result.tex);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function compile() {
    setCompiling(true);
    setCompileError(null);
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    setPdfUrl(null);
    try {
      const blob = await api.compileCv(result.tex, result.engine, result.template_id);
      setPdfUrl(URL.createObjectURL(blob));
    } catch (err) {
      setCompileError({ message: err.message, log: err.log, errors: err.errors });
    } finally {
      setCompiling(false);
    }
  }

  if (!result) return null;

  return (
    <div className="page-root">
      <LogoutBar username={username} />

      <div className="page-content">
        <div className="page-heading">
          <h1>Your CV is ready</h1>
          <p className="sub">
            Generated with template <strong>{result.template_id}</strong> · compile engine{" "}
            <strong>{result.engine}</strong>
          </p>
        </div>

        <div className="card" style={{ marginBottom: 24 }}>
          <div className="row" style={{ marginBottom: 12 }}>
            <button className="primary" onClick={compile} disabled={compiling}>
              {compiling ? "Compiling…" : "Compile to PDF"}
            </button>
            <button className="secondary" onClick={copyTex}>
              {copied ? "Copied!" : "Copy LaTeX"}
            </button>
            <button className="ghost" onClick={() => navigate("/onboarding/templates")}>
              Back to templates
            </button>
          </div>

          {compileError && (
            <div className="card" style={{ marginBottom: 12, borderColor: "var(--error)" }}>
              <p className="error">{compileError.message}</p>
              {Array.isArray(compileError.errors) && compileError.errors.length > 0 && (
                <ul style={{ fontSize: "0.85rem" }}>
                  {compileError.errors.map((e, i) => (
                    <li key={i}>
                      {e.file ? `${e.file}:${e.line} — ` : ""}
                      {e.message}
                    </li>
                  ))}
                </ul>
              )}
              {compileError.log && (
                <pre style={{ maxHeight: 240, overflow: "auto", fontSize: "0.75rem" }}>{compileError.log}</pre>
              )}
            </div>
          )}

          {pdfUrl && (
            <div style={{ marginBottom: 12 }}>
              <a className="primary" href={pdfUrl} download="resume.pdf" style={{ display: "inline-block", marginBottom: 12 }}>
                Download PDF
              </a>
              <embed src={pdfUrl} type="application/pdf" width="100%" height="600" />
            </div>
          )}
        </div>

        <div className="card">
          <pre style={{ maxHeight: 480, overflow: "auto", fontSize: "0.8rem", whiteSpace: "pre-wrap" }}>
            {result.tex}
          </pre>
        </div>
      </div>
    </div>
  );
}
