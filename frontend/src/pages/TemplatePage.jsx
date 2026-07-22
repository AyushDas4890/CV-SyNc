import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import LogoutBar from "../components/LogoutBar.jsx";
import "../styles.css";

const TEMPLATES = [
  { id: "jake",       name: "Jake's Resume" },
  { id: "dphang",     name: "dphang CV" },
  { id: "anubhav",    name: "Resume by Anubhav" },
  { id: "altacv",     name: "AltaCV" },
  { id: "moderncv",   name: "ModernCV" },
  { id: "plushcv",    name: "PlushCV" },
  { id: "deedy",      name: "Deedy CV" },
  { id: "awesome-cv", name: "Awesome CV" },
];

const CARD_WIDTH  = 220; // px — card width
const CARD_GAP    = 20;  // px — gap between cards
const SCROLL_STEP = CARD_WIDTH + CARD_GAP;

export default function TemplatePage() {
  const [previewing, setPreviewing]   = useState(null);
  const [chosen, setChosen]           = useState(null);
  const [username, setUsername]       = useState("");
  const [pageCounts, setPageCounts]   = useState({});
  const [canLeft, setCanLeft]         = useState(false);
  const [canRight, setCanRight]       = useState(true);
  const navigate = useNavigate();

  const scrollRef   = useRef(null);
  const isDragging  = useRef(false);
  const startX      = useRef(0);
  const scrollStart = useRef(0);

  useEffect(() => {
    api.me()
      .then((res) => setUsername(res.githubUsername))
      .catch(() => navigate("/auth"));

    fetch("/template-previews/manifest.json")
      .then((res) => (res.ok ? res.json() : {}))
      .then(setPageCounts)
      .catch(() => setPageCounts({}));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep arrow enable/disable in sync with scroll position
  function updateArrows() {
    const el = scrollRef.current;
    if (!el) return;
    setCanLeft(el.scrollLeft > 4);
    setCanRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 4);
  }

  function scrollBy(dir) {
    scrollRef.current?.scrollBy({ left: dir * SCROLL_STEP, behavior: "smooth" });
  }

  // Drag-to-scroll
  function onMouseDown(e) {
    isDragging.current = true;
    startX.current     = e.pageX - scrollRef.current.offsetLeft;
    scrollStart.current = scrollRef.current.scrollLeft;
    scrollRef.current.style.cursor = "grabbing";
  }
  function onMouseUp()    { endDrag(); }
  function onMouseLeave() { endDrag(); }
  function endDrag() {
    isDragging.current = false;
    if (scrollRef.current) scrollRef.current.style.cursor = "grab";
  }
  function onMouseMove(e) {
    if (!isDragging.current) return;
    e.preventDefault();
    const x = e.pageX - scrollRef.current.offsetLeft;
    scrollRef.current.scrollLeft = scrollStart.current - (x - startX.current) * 1.4;
  }

  function pageCountFor(id) { return pageCounts[id] || 1; }

  function confirmSelection() {
    setChosen(previewing.id);
    setPreviewing(null);
  }

  return (
    <div className="page-root">
      <LogoutBar username={username} />

      <div className="page-content">
        {/* Step indicator */}
        <div className="step-indicator">
          {["Account", "Profile", "Experience", "GitHub"].map((label) => (
            <div key={label} style={{ display: "flex", alignItems: "center" }}>
              <div className="step-item done">
                <div className="step-dot">✓</div>
                <span>{label}</span>
              </div>
              <div className="step-connector" />
            </div>
          ))}
          <div className="step-item active">
            <div className="step-dot">5</div>
            <span>Template</span>
          </div>
        </div>

        {/* Heading */}
        <div className="page-heading">
          <h1>Choose a CV template</h1>
          <p className="sub">Click any card to preview the full layout, then select it.</p>
        </div>
      </div>

      {/* ── Full-bleed carousel ───────────────────────────── */}
      <div className="template-carousel-section">

        {/* Arrow — left */}
        <button
          className="carousel-arrow carousel-arrow-left"
          onClick={() => scrollBy(-1)}
          disabled={!canLeft}
          aria-label="Scroll left"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>

        {/* Scrollable track */}
        <div
          className="template-track"
          ref={scrollRef}
          onScroll={updateArrows}
          onMouseDown={onMouseDown}
          onMouseUp={onMouseUp}
          onMouseLeave={onMouseLeave}
          onMouseMove={onMouseMove}
        >
          {TEMPLATES.map((t) => (
            <div
              key={t.id}
              className={`template-card ${chosen === t.id ? "chosen" : ""}`}
              onClick={() => !isDragging.current && setPreviewing(t)}
            >
              {chosen === t.id && <span className="chosen-badge">✓ Selected</span>}
              {pageCountFor(t.id) > 1 && (
                <span className="page-count-badge">{pageCountFor(t.id)}p</span>
              )}
              <div className="thumb">
                <img src={`/template-previews/${t.id}.png`} alt={t.name} draggable={false} />
              </div>
              <div className="label">{t.name}</div>
            </div>
          ))}
        </div>

        {/* Arrow — right */}
        <button
          className="carousel-arrow carousel-arrow-right"
          onClick={() => scrollBy(1)}
          disabled={!canRight}
          aria-label="Scroll right"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>

      {/* CTA — back inside constrained content */}
      <div className="page-content">
        <div className="row" style={{ marginTop: 28 }}>
          <button className="primary" disabled={!chosen}>
            {chosen
              ? `Continue with ${TEMPLATES.find((t) => t.id === chosen).name}`
              : "Select a template above"}
          </button>
        </div>
        {!chosen && (
          <p className="notice" style={{ textAlign: "center", marginTop: 8 }}>
            Click a template card to preview and select
          </p>
        )}
      </div>

      {/* Preview modal */}
      {previewing && (
        <div className="modal-backdrop" onClick={() => setPreviewing(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{previewing.name}</h2>
              <button className="modal-close" onClick={() => setPreviewing(null)}>×</button>
            </div>
            <div className="modal-body">
              {Array.from({ length: pageCountFor(previewing.id) }, (_, i) => i + 1).map((page) => (
                <img
                  key={page}
                  src={
                    page === 1
                      ? `/template-previews/${previewing.id}.png`
                      : `/template-previews/${previewing.id}-p${page}.png`
                  }
                  alt={`${previewing.name} page ${page}`}
                  className="modal-page-image"
                />
              ))}
            </div>
            <div className="modal-footer">
              <button className="secondary" onClick={() => setPreviewing(null)}>Cancel</button>
              <button className="primary" onClick={confirmSelection}>Select this template</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
