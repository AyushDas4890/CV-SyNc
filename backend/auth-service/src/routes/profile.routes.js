const { Router } = require("express");
const profileController = require("../controllers/profile.controller");

const router = Router();

// POST /api/profile  — save student profile + education
router.post("/", profileController.save);

// GET  /api/profile  — retrieve saved student profile + education
router.get("/", profileController.get);

module.exports = router;
