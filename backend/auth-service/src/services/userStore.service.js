/**
 * PLACEHOLDER user store.
 *
 * GitHub OAuth is now the login itself (Ayush's call: skip Google, use GitHub
 * as the sole auth method — supersedes 02-auth-service.md's original
 * "email/password primary, GitHub identity separate" design for V1).
 *
 * Real persistence isn't built yet — this in-memory Map stands in for the
 * MySQL `users` table. Restarting the server drops all sessions' users.
 *
 * TODO when real persistence is added (06-build-plan Phase C, revised):
 *   - replace this Map with a MySQL `users` table keyed on github_id
 *   - columns: id, github_id UNIQUE, github_username, github_token, created_at
 *   - github_token should be encrypted at rest, not stored plain like this
 */

const usersByGithubId = new Map(); // githubId -> { id, githubId, githubUsername, githubToken }

function findOrCreateByGithubId(githubId, { username, token }) {
  const existing = usersByGithubId.get(githubId);
  if (existing) {
    existing.githubToken = token; // token can rotate/refresh on re-login
    existing.githubUsername = username;
    return existing;
  }
  const user = { id: `u_${githubId}`, githubId, githubUsername: username, githubToken: token };
  usersByGithubId.set(githubId, user);
  return user;
}

function getById(userId) {
  for (const user of usersByGithubId.values()) {
    if (user.id === userId) return user;
  }
  return null;
}

function getGithubToken(userId) {
  return getById(userId)?.githubToken || null;
}

module.exports = { findOrCreateByGithubId, getById, getGithubToken };
