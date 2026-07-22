const API_URL = import.meta.env.VITE_API_URL || "http://localhost:4000";
const LLM_BRAIN_URL = import.meta.env.VITE_LLM_BRAIN_URL || "http://localhost:8000";
const CV_BUILDER_URL = import.meta.env.VITE_CV_BUILDER_URL || "http://localhost:3000";

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    credentials: "include",
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const err = new Error(data.error || `Request failed with status ${res.status}`);
    err.status = res.status;
    throw err;
  }

  return data;
}

// CV_BRAIN is a separate service (FastAPI, no session cookie of its own) —
// no `credentials: include` here, and its CORS config (allow_origins=["*"])
// would reject credentialed requests anyway.
async function llmRequest(path, options = {}) {
  const res = await fetch(`${LLM_BRAIN_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const err = new Error(data.detail || `CV_BRAIN request failed with status ${res.status}`);
    err.status = res.status;
    throw err;
  }

  return data;
}

// Fetch READMEs for selected repos via the backend (needs the user's GitHub
// token, which only auth-service holds). Best-effort: a repo whose README
// fetch fails (network blip, rate limit) just gets readme_content: "" rather
// than failing the whole CV generation — CV_BRAIN already treats a missing
// README as "fall back to manifests/commits/file tree" (see latex_generator
// prompt), so it degrades rather than breaks.
async function fetchReadmesForRepos(repos) {
  const results = await Promise.allSettled(
    repos.map((r) => {
      const [owner, name] = (r.fullName || "").split("/");
      if (!owner || !name) return Promise.resolve("");
      return request(`/api/auth/github/repos/${owner}/${name}/readme`).then((d) => d.readme || "");
    })
  );
  return results.map((r) => (r.status === "fulfilled" ? r.value : ""));
}

// ── Build CV_BRAIN's GenerateCvRequest from onboarding data cached in localStorage ──
// See app/models.py in CV_BRAIN (UserProfile, RepoDetail, AchievementEntry) for the
// target shape. Async because it fetches READMEs for the selected repos.
async function buildGenerateCvPayload({ targetRole = "", targetPages = 1 } = {}) {
  const studentProfile = JSON.parse(localStorage.getItem("cv_sync_student_profile") || "{}");
  const experience = JSON.parse(localStorage.getItem("cv_sync_experience") || "[]");
  const selectedRepos = JSON.parse(localStorage.getItem("cv_sync_selected_repos") || "[]");
  const template = JSON.parse(localStorage.getItem("cv_sync_template") || "{}");

  const { profile = {}, education = [], achievements = [], certificates = [] } = studentProfile;

  if (!template.brainId) {
    throw new Error("No template selected — pick a template before generating a CV.");
  }
  if (selectedRepos.length === 0) {
    throw new Error("No repos selected — go back and pick at least one repo.");
  }

  const readmes = await fetchReadmesForRepos(selectedRepos);

  const user_profile = {
    name: profile.fullName || "",
    email: profile.email || "",
    phone: profile.phone || "",
    location: "",
    linkedin: profile.linkedinUrl || "",
    github: profile.githubUrl || "",
    portfolio: "",
    summary: "",
    education: education.map((e) => ({
      institution: e.institution || "",
      degree: [e.degree, e.fieldOfStudy].filter(Boolean).join(", "),
      location: "",
      dates: e.dates || "",
      gpa: e.gpa || "",
    })),
    experience: experience.map((e) => ({
      company: e.company || "",
      role: e.role || "",
      location: "",
      dates: e.dates || "",
      // Textarea is free text — split into lines so CV_BRAIN gets discrete bullets,
      // falling back to the whole string if the user didn't use newlines.
      bullets: (e.bullets || "")
        .split("\n")
        .map((b) => b.trim())
        .filter(Boolean),
    })),
    // Requires the CV_BRAIN patch in kb/relay/cv_brain-achievements-patch —
    // UserProfile has no `achievements` field until that's applied there.
    achievements: achievements
      .filter((a) => a.title || a.description)
      .map((a) => ({ title: a.title || "", description: a.description || "", date: a.date || "" })),
    skills: {},
    certifications: certificates
      .filter((c) => c.name)
      .map((c) => [c.name, c.issuer, c.date].filter(Boolean).join(" — ")),
  };

  const selected_repos = selectedRepos.map((r, i) => ({
    id: r.id,
    name: r.name || "",
    full_name: r.fullName || "",
    description: r.description || "",
    language: r.language || "",
    stars: r.stars || 0,
    topics: r.topics || [],
    url: r.url || "",
    readme_content: readmes[i] || "",
    user_notes: "",
  }));

  return {
    user_profile,
    selected_repos,
    template_id: template.brainId,
    target_role: targetRole,
    target_pages: targetPages,
  };
}

// CV_BUILDER's /api/compile returns a raw PDF binary on success, or JSON on
// failure (400/413/422/500) — can't reuse request()/llmRequest() which both
// assume JSON back. templateId is optional but lets the server infer the
// right engine (xelatex/lualatex/pdflatex) if `engine` is left out.
async function compileCv(tex, engine, templateId) {
  const res = await fetch(`${CV_BUILDER_URL}/api/compile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tex, engine, templateId }),
  });

  if (res.ok) {
    return res.blob(); // application/pdf
  }

  const data = await res.json().catch(() => ({}));
  const err = new Error(data.error || `CV_BUILDER compile failed with status ${res.status}`);
  err.status = res.status;
  err.log = data.log;
  err.errors = data.errors; // [{file, line, message}] on 422
  throw err;
}

export const api = {
  // backend returns { ok, user }, not the user object itself — unwrap here
  // once instead of in every page that calls this.
  me() {
    return request("/api/auth/me").then((data) => data.user);
  },

  logout() {
    return request("/api/auth/logout", { method: "POST" });
  },

  githubRepos() {
    return request("/api/auth/github/repos");
  },

  // ── Auth URLs (full-page navigations, not fetch) ──
  githubLoginUrl() {
    return `${API_URL}/api/auth/github`;
  },

  googleLoginUrl() {
    return `${API_URL}/api/auth/google`;
  },

  // ── Email / Password (JSON fetch) ────────────────
  emailLogin(email, password) {
    return request("/api/auth/email/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  emailRegister(email, password, displayName) {
    return request("/api/auth/email/register", {
      method: "POST",
      body: JSON.stringify({ email, password, displayName }),
    });
  },

  // ── Student Profile ──────────────────────────────
  saveProfile(data) {
    return request("/api/profile", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  getProfile() {
    return request("/api/profile");
  },

  // ── CV_BRAIN ──────────────────────────────────────────────
  listCvTemplates() {
    return llmRequest("/api/templates");
  },

  async generateCv(opts) {
    const payload = await buildGenerateCvPayload(opts);
    return llmRequest("/api/generate-cv", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // ── CV_BUILDER ────────────────────────────────────────────
  compileCv(tex, engine, templateId) {
    return compileCv(tex, engine, templateId);
  },
};
