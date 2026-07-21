const googleService = require("../services/googleAuth.service");
const userStore = require("../services/userStore.service");
const config = require("../config/env");

const pendingStates = new Map(); // csrf state token → timestamp

// ── GET /api/auth/google ──────────────────────
exports.login = (req, res) => {
  if (!config.google.clientId) {
    return res.status(503).json({ error: "Google OAuth is not configured on this server." });
  }
  const state = googleService.generateState();
  pendingStates.set(state, Date.now());
  // clean up states older than 10 minutes
  for (const [k, t] of pendingStates) {
    if (Date.now() - t > 10 * 60 * 1000) pendingStates.delete(k);
  }
  const url = googleService.buildGoogleAuthorizeUrl(state);
  res.redirect(url);
};

// ── GET /api/auth/google/callback ─────────────
exports.callback = async (req, res) => {
  const { code, state, error } = req.query;

  if (error) {
    console.warn("[google] oauth error from google:", error);
    return res.redirect(`${config.frontendUrl}/auth?error=google_denied`);
  }
  if (!code || !pendingStates.has(state)) {
    return res.redirect(`${config.frontendUrl}/auth?error=invalid_state`);
  }
  pendingStates.delete(state);

  try {
    const tokenData = await googleService.exchangeCodeForToken(code);
    const googleUser = await googleService.fetchGoogleUser(tokenData.access_token);

    const user = userStore.findOrCreateByGoogleId(googleUser.sub, {
      email: googleUser.email,
      name: googleUser.name,
      picture: googleUser.picture,
      accessToken: tokenData.access_token,
    });

    req.session.userId = user.id;
    res.redirect(config.frontendUrl);
  } catch (err) {
    console.error("[google] callback error:", err.message);
    res.redirect(`${config.frontendUrl}/auth?error=google_failed`);
  }
};
