const bcrypt = require("bcryptjs");

/**
 * Unified user store supporting three auth methods:
 *   1. GitHub OAuth   — keyed on github_id
 *   2. Google OAuth   — keyed on google_id
 *   3. Email/Password — keyed on email (lowercased)
 *
 * Storage: in-memory Map for development.
 * TODO (Phase C): replace with MySQL `users` table with columns:
 *   id, github_id UNIQUE, google_id UNIQUE, email UNIQUE,
 *   password_hash, display_name, avatar_url, github_token,
 *   google_token, created_at
 */

const usersById = new Map();       // id → user object
const byGithubId = new Map();      // github_id → id
const byGoogleId = new Map();      // google_id → id
const byEmail = new Map();         // email (lower) → id

function _nextId() {
  return `u_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

// ── GitHub OAuth ──────────────────────────────────────────────
function findOrCreateByGithubId(githubId, { username, token, avatarUrl } = {}) {
  if (byGithubId.has(githubId)) {
    const user = usersById.get(byGithubId.get(githubId));
    user.githubToken = token;
    user.githubUsername = username;
    return user;
  }
  const id = _nextId();
  const user = {
    id,
    githubId,
    githubUsername: username,
    githubToken: token,
    displayName: username,
    avatarUrl: avatarUrl || null,
    provider: "github",
  };
  usersById.set(id, user);
  byGithubId.set(githubId, id);
  return user;
}

// ── Google OAuth ──────────────────────────────────────────────
function findOrCreateByGoogleId(googleId, { email, name, picture, accessToken } = {}) {
  if (byGoogleId.has(googleId)) {
    const user = usersById.get(byGoogleId.get(googleId));
    user.googleToken = accessToken;
    return user;
  }
  const id = _nextId();
  const normalEmail = (email || "").toLowerCase();
  const user = {
    id,
    googleId,
    email: normalEmail,
    displayName: name || normalEmail,
    avatarUrl: picture || null,
    googleToken: accessToken,
    provider: "google",
  };
  usersById.set(id, user);
  byGoogleId.set(googleId, id);
  if (normalEmail) byEmail.set(normalEmail, id);
  return user;
}

// ── Email / Password ──────────────────────────────────────────
async function createEmailUser(email, plainPassword, displayName) {
  const normalEmail = email.toLowerCase().trim();
  if (byEmail.has(normalEmail)) {
    throw new Error("EMAIL_TAKEN");
  }
  const passwordHash = await bcrypt.hash(plainPassword, 12);
  const id = _nextId();
  const user = {
    id,
    email: normalEmail,
    passwordHash,
    displayName: displayName || normalEmail.split("@")[0],
    avatarUrl: null,
    provider: "email",
  };
  usersById.set(id, user);
  byEmail.set(normalEmail, id);
  return user;
}

async function verifyEmailUser(email, plainPassword) {
  const normalEmail = email.toLowerCase().trim();
  const id = byEmail.get(normalEmail);
  if (!id) return null;
  const user = usersById.get(id);
  if (!user || !user.passwordHash) return null;
  const ok = await bcrypt.compare(plainPassword, user.passwordHash);
  return ok ? user : null;
}

// ── Generic lookups ───────────────────────────────────────────
function getById(userId) {
  return usersById.get(userId) || null;
}

function getGithubToken(userId) {
  return getById(userId)?.githubToken || null;
}

/**
 * Safe public profile — strip tokens and password hash before sending to client.
 */
function publicProfile(user) {
  if (!user) return null;
  const { passwordHash, githubToken, googleToken, ...safe } = user;
  return safe;
}

module.exports = {
  findOrCreateByGithubId,
  findOrCreateByGoogleId,
  createEmailUser,
  verifyEmailUser,
  getById,
  getGithubToken,
  publicProfile,
};
