const express = require("express");
const githubController = require("../controllers/githubAuth.controller");
const emailController = require("../controllers/emailAuth.controller");
const requireSession = require("../middleware/requireSession");

const router = express.Router();

// ── GitHub OAuth ──────────────────────────────────────────────
// login/callback must NOT require a session — there isn't one yet
router.get("/github", githubController.login);
router.get("/github/callback", githubController.callback);

// ── Email / Password ──────────────────────────────────────────
router.post("/email/register", emailController.register);
router.post("/email/login", emailController.login);

// ── Session ───────────────────────────────────────────────────
router.get("/me", githubController.me);
router.post("/logout", githubController.logout);

// ── GitHub Repos (needs active session + GitHub token) ────────
router.get("/github/repos", requireSession, githubController.listRepos);
router.get("/github/repos/:owner/:repo/readme", requireSession, githubController.getRepoReadme);

module.exports = router;
