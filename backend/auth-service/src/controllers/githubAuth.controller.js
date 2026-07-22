const githubAuthService = require("../services/githubAuth.service");
const userStore = require("../services/userStore.service");
const config = require("../config/env");

// GET /api/auth/github  — "Continue with GitHub" login button hits this.
// No requireSession here: this IS how you get a session now.
function login(req, res) {
  const state = githubAuthService.generateState();
  req.session.githubOauthState = state; // CSRF check on callback
  res.redirect(githubAuthService.buildAuthorizeUrl(state));
}

// GET /api/auth/github/callback
async function callback(req, res) {
  const { code, state } = req.query;

  if (!code) {
    return res.status(400).json({ ok: false, error: "missing code" });
  }
  if (!state || state !== req.session.githubOauthState) {
    // CSRF / replay guard
    return res.status(400).json({ ok: false, error: "invalid state" });
  }
  delete req.session.githubOauthState;

  try {
    const token = await githubAuthService.exchangeCodeForToken(code);
    const ghUser = await githubAuthService.fetchGithubUser(token);

    const user = userStore.findOrCreateByGithubId(String(ghUser.id), {
      username: ghUser.login,
      token,
    });

    // regenerate session id on login — prevents session fixation (an attacker
    // who set req.session.githubOauthState pre-login can't reuse that session)
    req.session.regenerate((err) => {
      if (err) {
        console.error("[github oauth callback] session regenerate failed", err.message);
        return res.redirect(`${config.frontendUrl}/auth?error=session`);
      }
      req.session.userId = user.id;
      // land on Profile next, not the repo picker — GitHub login already
      // happened, so /onboarding/github is further downstream
      res.redirect(`${config.frontendUrl}/onboarding/profile?login=1`);
    });
  } catch (err) {
    console.error("[github oauth callback]", err.message);
    res.redirect(`${config.frontendUrl}/auth?error=oauth`);
  }
}

// GET /api/auth/me — is there a logged-in user, and who
function me(req, res) {
  if (!req.session?.userId) {
    return res.status(401).json({ ok: false, error: "not authenticated" });
  }
  const user = userStore.getById(req.session.userId);
  if (!user) {
    return res.status(401).json({ ok: false, error: "not authenticated" });
  }
  res.json({ ok: true, user: userStore.publicProfile(user) });
}

// POST /api/auth/logout
function logout(req, res) {
  req.session.destroy((err) => {
    if (err) {
      console.error("[logout] destroy failed", err.message);
      return res.status(500).json({ ok: false, error: "logout failed" });
    }
    res.clearCookie("connect.sid");
    res.json({ ok: true });
  });
}

// GET /api/auth/github/repos
async function listRepos(req, res) {
  const token = userStore.getGithubToken(req.session.userId);
  if (!token) {
    return res.status(400).json({ ok: false, error: "github not connected" });
  }

  try {
    const page = Number(req.query.page) || 1;
    const repos = await githubAuthService.fetchUserRepos(token, { page });
    res.json({ ok: true, repos });
  } catch (err) {
    console.error("[github repos]", err.message);
    res.status(502).json({ ok: false, error: "failed to fetch repos from github" });
  }
}

// GET /api/auth/github/repos/:owner/:repo/readme
async function getRepoReadme(req, res) {
  const token = userStore.getGithubToken(req.session.userId);
  if (!token) {
    return res.status(400).json({ ok: false, error: "github not connected" });
  }

  const { owner, repo } = req.params;
  try {
    const readme = await githubAuthService.fetchRepoReadme(token, owner, repo);
    res.json({ ok: true, readme });
  } catch (err) {
    console.error("[github repo readme]", err.message);
    res.status(502).json({ ok: false, error: "failed to fetch readme from github" });
  }
}

module.exports = { login, callback, me, logout, listRepos, getRepoReadme };
