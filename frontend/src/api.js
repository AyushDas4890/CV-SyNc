const API_URL = import.meta.env.VITE_API_URL || "http://localhost:4000";

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

export const api = {
  me() {
    return request("/api/auth/me");
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
};
