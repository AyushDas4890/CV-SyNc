const logger = require('../config/logger.config');
const latexService = require('../service/latex.service');

class LatexController {
  async compile(req, res) {
    let { tex, extraFiles, engine, templateId } = req.body || {};

    if (!engine && templateId) {
      if (templateId.includes('Awesome_CV') || templateId.includes('Deedy_CV') || templateId.includes('PlushCV')) {
        engine = 'xelatex';
      } else if (templateId.includes('AltaCV')) {
        engine = 'lualatex';
      } else {
        engine = 'pdflatex';
      }
    }

    if (typeof tex !== 'string' || tex.trim().length === 0) {
      return res
        .status(400)
        .json({ ok: false, error: "Missing 'tex' source in request body." });
    }

    if (tex.length > 2_000_000) {
      return res.status(413).json({ ok: false, error: 'Document too large.' });
    }

    try {
      logger.info('request reached handler');
      const result = await latexService.compileLatex(tex, extraFiles, engine, templateId);
      logger.info('request sent to service');
      if (result.success) {
        res.setHeader('Content-Type', 'application/pdf');
        // Page count comes free from the latexmk log. Exposed so callers can
        // check the document length without re-parsing the PDF. Expose-Headers
        // is required or browsers hide it from cross-origin JS.
        if (result.pageCount != null) {
          res.setHeader('X-Page-Count', String(result.pageCount));
          res.setHeader('Access-Control-Expose-Headers', 'X-Page-Count');
        }
        logger.info('Sucessfully sent response ack from controler');
        return res.send(result.pdfBuffer);
      } else {
        logger.error({ log: result.log, errors: result.errors }, 'LaTeX compilation failed');
        return res.status(422).json({
          ok: false,
          log: result.log,
          errors: result.errors,
        });
      }
    } catch (err) {
      console.error('Compilation error:', err);
      return res.status(500).json({ ok: false, error: err.message });
    }
  }
}

module.exports = new LatexController();
