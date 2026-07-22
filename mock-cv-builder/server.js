/**
 * Mock CV_BUILDER server — port 3000
 *
 * Serves local .tex templates from the cv-templates/ folder so that
 * CV_BRAIN can run without needing the real CV_BUILDER repo.
 *
 * GET /api/health                       → { ok: true }
 * GET /api/templates/:id/full           → { success: true, tex: "..." }
 * POST /api/compile { tex: string }     → returns PDF binary (calls local latexmk if available)
 */

const express = require("express");
const fs = require("fs");
const path = require("path");

const app = express();
app.use(express.json({ limit: "10mb" }));

// --------------------------------------------------------------------------
// Template ID → folder name mapping (mirrors CV_BRAIN's template_registry.py)
// --------------------------------------------------------------------------
const TEMPLATE_FOLDER_MAP = {
  Jake_s_Resume__3_: "jake",
  AltaCV_Template__1_: "altacv",
  Deedy_CV__1_: "deedy",
  Awesome_CV__3_: "awesome-cv",
  PlushCV__2_: "plushcv",
  ModernCV_and_Cover_Letter_Template__2_: null, // not in local cv-templates
  Resume_Template_by_Anubhav__2_: "anubhav",
  dphang_CV_Template__1_: "dphang",
};

// Resolve template files relative to the cv-templates directory
const TEMPLATES_ROOT = path.resolve(__dirname, "../cv-templates");

// --------------------------------------------------------------------------
// Health check
// --------------------------------------------------------------------------
app.get("/api/health", (req, res) => {
  res.json({ ok: true, service: "mock-cv-builder" });
});

// --------------------------------------------------------------------------
// GET /api/templates/:id/full
// Returns the concatenated .tex content for the requested template ID
// --------------------------------------------------------------------------
app.get("/api/templates/:id/full", (req, res) => {
  const { id } = req.params;
  const folder = TEMPLATE_FOLDER_MAP[id];

  if (folder === undefined) {
    return res.status(404).json({ success: false, error: `Unknown template ID: ${id}` });
  }

  if (folder === null) {
    return res.status(404).json({ success: false, error: `Template '${id}' not available locally.` });
  }

  const templateDir = path.join(TEMPLATES_ROOT, folder);

  // Read all .tex files in the directory and concatenate them
  let texContent = "";

  try {
    const files = fs.readdirSync(templateDir);
    const texFiles = files.filter((f) => f.endsWith(".tex")).sort();

    if (texFiles.length === 0) {
      return res.status(404).json({ success: false, error: `No .tex files found in template folder: ${folder}` });
    }

    for (const file of texFiles) {
      const filePath = path.join(templateDir, file);
      const content = fs.readFileSync(filePath, "utf8");
      texContent += content + "\n";
    }

    console.log(`[mock-cv-builder] Served template '${id}' from '${folder}' (${texContent.length} chars)`);
    return res.json({ success: true, tex: texContent, template_id: id, folder });
  } catch (err) {
    console.error(`[mock-cv-builder] Error reading template '${id}':`, err.message);
    return res.status(500).json({ success: false, error: err.message });
  }
});

// --------------------------------------------------------------------------
// POST /api/compile  { tex: string }
// Stub — returns 503 with a clear message since latexmk is not guaranteed.
// The frontend calls CV_BUILDER for compilation; this mock lets generation
// work. Compilation will need Docker or a real latexmk install.
// --------------------------------------------------------------------------
app.post("/api/compile", (req, res) => {
  const { tex } = req.body;
  if (!tex) {
    return res.status(400).json({ ok: false, error: "tex field is required" });
  }
  // If you have latexmk installed locally you can add real compilation here.
  res.status(503).json({
    ok: false,
    error: "Compilation not available on mock server. Run the real CV_BUILDER Docker image or install latexmk.",
  });
});

// --------------------------------------------------------------------------
// List all available templates (bonus endpoint)
// --------------------------------------------------------------------------
app.get("/api/templates", (req, res) => {
  const available = Object.entries(TEMPLATE_FOLDER_MAP)
    .filter(([, folder]) => folder !== null)
    .map(([id, folder]) => ({ id, folder }));
  res.json({ ok: true, templates: available });
});

// --------------------------------------------------------------------------
// Start
// --------------------------------------------------------------------------
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`[mock-cv-builder] Listening on http://localhost:${PORT}`);
  console.log(`[mock-cv-builder] Templates root: ${TEMPLATES_ROOT}`);
  console.log("[mock-cv-builder] Available routes:");
  console.log("  GET  /api/health");
  console.log("  GET  /api/templates");
  console.log("  GET  /api/templates/:id/full");
  console.log("  POST /api/compile  (stub — returns 503)");
});
