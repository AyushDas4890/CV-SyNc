const express = require("express");
const controller = require("../controllers/githubAuth.controller");
const requireSession = require("../middleware/requireSession");

const router = express.Router();

// GitHub OAuth IS the login now (Ayush: skip Google, GitHub-only auth for V1).
// login/callback must NOT require a session — there isn't one yet, that's the point.
router.get("/github", controller.login);
router.get("/github/callback", controller.callback);

router.get("/me", controller.me);
router.post("/logout", controller.logout);

// needs an existing session — set by the callback above
router.get("/github/repos", requireSession, controller.listRepos);

module.exports = router;
