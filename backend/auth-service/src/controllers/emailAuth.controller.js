const userStore = require("../services/userStore.service");

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// ── POST /api/auth/email/register ─────────────
exports.register = async (req, res) => {
  const { email, password, displayName } = req.body || {};

  if (!email || !password) {
    return res.status(400).json({ error: "email and password are required." });
  }
  if (!EMAIL_RE.test(email)) {
    return res.status(400).json({ error: "Invalid email address." });
  }
  if (password.length < 8) {
    return res.status(400).json({ error: "Password must be at least 8 characters." });
  }

  try {
    const user = await userStore.createEmailUser(email, password, displayName);
    req.session.userId = user.id;
    return res.status(201).json({ ok: true, user: userStore.publicProfile(user) });
  } catch (err) {
    if (err.message === "EMAIL_TAKEN") {
      return res.status(409).json({ error: "An account with this email already exists." });
    }
    console.error("[email/register]", err.message);
    return res.status(500).json({ error: "Registration failed. Please try again." });
  }
};

// ── POST /api/auth/email/login ────────────────
exports.login = async (req, res) => {
  const { email, password } = req.body || {};

  if (!email || !password) {
    return res.status(400).json({ error: "email and password are required." });
  }

  try {
    const user = await userStore.verifyEmailUser(email, password);
    if (!user) {
      // deliberately vague — don't reveal whether email exists
      return res.status(401).json({ error: "Invalid email or password." });
    }
    req.session.userId = user.id;
    return res.json({ ok: true, user: userStore.publicProfile(user) });
  } catch (err) {
    console.error("[email/login]", err.message);
    return res.status(500).json({ error: "Login failed. Please try again." });
  }
};
