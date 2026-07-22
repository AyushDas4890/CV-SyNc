const axios = require("axios");
const crypto = require("crypto");
const https = require("https");
const config = require("../config/env");

const httpsAgent = new https.Agent({
  rejectUnauthorized: process.env.NODE_TLS_REJECT_UNAUTHORIZED !== "0" && false, // relaxed for corporate/proxy SSL inspection
});

const AUTHORIZE_URL = "https://github.com/login/oauth/authorize";
const TOKEN_URL = "https://github.com/login/oauth/access_token";
const API_BASE = "https://api.github.com";

function buildAuthorizeUrl(state) {
  const params = new URLSearchParams({
    client_id: config.github.clientId,
    redirect_uri: config.github.callbackUrl,
    scope: config.github.scope,
    state,
    // Force GitHub to always show its login/account-chooser screen.
    // Without this, GitHub silently re-authorizes if the user is already
    // logged into github.com and has previously approved this OAuth app.
    allow_signup: "true",
  });
  // Append login= with no value — GitHub interprets this as "show the login
  // prompt even if the user already has an active GitHub session".
  return `${AUTHORIZE_URL}?${params.toString()}&login=`;
}

function generateState() {
  return crypto.randomBytes(16).toString("hex");
}

async function exchangeCodeForToken(code) {
  const res = await axios.post(
    TOKEN_URL,
    {
      client_id: config.github.clientId,
      client_secret: config.github.clientSecret,
      code,
      redirect_uri: config.github.callbackUrl,
    },
    {
      headers: { Accept: "application/json" },
      httpsAgent,
    }
  );

  if (res.data.error) {
    // GitHub returns 200 with an error body on failure, not a 4xx — check explicitly
    throw new Error(`github oauth error: ${res.data.error_description || res.data.error}`);
  }
  return res.data.access_token;
}

async function fetchGithubUser(token) {
  const res = await axios.get(`${API_BASE}/user`, {
    headers: { Authorization: `Bearer ${token}` },
    httpsAgent,
  });
  return res.data; // includes .login (username)
}

async function fetchUserRepos(token, { page = 1, perPage = 30 } = {}) {
  const res = await axios.get(`${API_BASE}/user/repos`, {
    headers: { Authorization: `Bearer ${token}` },
    params: { visibility: "public", sort: "updated", per_page: perPage, page },
    httpsAgent,
  });
  return res.data.map((r) => ({
    id: r.id,
    name: r.name,
    fullName: r.full_name,
    description: r.description,
    language: r.language,
    stars: r.stargazers_count,
    topics: r.topics || [],
    url: r.html_url,
    updatedAt: r.updated_at,
  }));
}

// GET /repos/{owner}/{repo}/readme — used to feed real project context into
// CV_BRAIN's bullet generation (kb/05-llm-rag.md fetch step).
// Returns "" (not an error) for repos with no README, so callers can just
// drop it into the payload without special-casing.
async function fetchRepoReadme(token, owner, repo) {
  try {
    const res = await axios.get(`${API_BASE}/repos/${owner}/${repo}/readme`, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github.raw+json",
      },
      httpsAgent,
    });
    // Accept: raw+json gives plain text directly; res.data is a string
    return typeof res.data === "string" ? res.data : "";
  } catch (err) {
    if (err.response?.status === 404) return ""; // no README — not an error
    throw err;
  }
}

module.exports = {
  buildAuthorizeUrl,
  generateState,
  exchangeCodeForToken,
  fetchGithubUser,
  fetchUserRepos,
  fetchRepoReadme,
};
