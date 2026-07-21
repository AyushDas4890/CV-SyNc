/**
 * Guards routes behind a logged-in session, per 02-auth-service.md:
 * cookie -> session_id -> session lookup -> 401 if missing/expired.
 *
 * Real signup/login isn't built yet (06-build-plan Phase C), so this reads
 * req.session.userId set by express-session — once real auth exists, this
 * middleware doesn't change, only what populates req.session.userId does.
 */
function requireSession(req, res, next) {
  if (!req.session || !req.session.userId) {
    return res.status(401).json({ ok: false, error: "not authenticated" });
  }
  next();
}

module.exports = requireSession;
