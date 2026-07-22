const userStore = require("../services/userStore.service");

/**
 * POST /api/profile
 * Body: { profile: {...}, education: [...], achievements: [...], certificates: [...] }
 * Saves the student profile data against the authenticated user's session.
 */
exports.save = (req, res) => {
  if (!req.session?.userId) {
    return res.status(401).json({ error: "not authenticated" });
  }

  // Was only forwarding { profile, education } — achievements/certificates were
  // silently dropped on every save even though ProfilePage.jsx sends all four.
  const { profile, education, achievements, certificates } = req.body || {};

  if (!profile && !education && !achievements && !certificates) {
    return res.status(400).json({ error: "No profile data provided." });
  }

  try {
    const saved = userStore.saveProfile(req.session.userId, { profile, education, achievements, certificates });
    return res.json({ ok: true, studentProfile: saved });
  } catch (err) {
    if (err.message === "USER_NOT_FOUND") {
      return res.status(401).json({ error: "not authenticated" });
    }
    console.error("[profile/save]", err.message);
    return res.status(500).json({ error: "Failed to save profile." });
  }
};

/**
 * GET /api/profile
 * Returns the saved student profile for the logged-in user.
 */
exports.get = (req, res) => {
  if (!req.session?.userId) {
    return res.status(401).json({ error: "not authenticated" });
  }

  const studentProfile = userStore.getProfile(req.session.userId);
  return res.json({ ok: true, studentProfile: studentProfile || null });
};
