const { randomUUID } = require('crypto');
const fs = require('fs/promises');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');
const logger = require('../config/logger.config');

const COMPILE_TIMEOUT_MS = parseInt(process.env.COMPILE_TIMEOUT_MS || '60000', 10); // default 60s
const MAX_LOG_CHARS = 20000;

function runLatexmk(dir, engine = 'pdflatex') {
  return new Promise((resolve) => {
    const engineFlag = engine === 'xelatex' ? '-xelatex' : (engine === 'lualatex' ? '-lualatex' : '-pdf');
    const args = [
      engineFlag,
      '-interaction=nonstopmode',
      '-halt-on-error',
      '-no-shell-escape',
      '-file-line-error',
      '-outdir=' + dir,
      'doc.tex',
    ];

    const child = spawn('latexmk', args, {
      cwd: dir,
      env: {
        ...process.env,
        openin_any: 'p',
        openout_any: 'p',
      },
    });

    let stdout = '';
    let stderr = '';
    let killedForTimeout = false;

    const timer = setTimeout(() => {
      killedForTimeout = true;
      child.kill('SIGKILL');
    }, COMPILE_TIMEOUT_MS);

    child.stdout.on('data', (d) => (stdout += d.toString()));
    child.stderr.on('data', (d) => (stderr += d.toString()));

    child.on('close', async () => {
      clearTimeout(timer);
      const pdfPath = path.join(dir, 'doc.pdf');
      const pdfExists = await fs
        .access(pdfPath)
        .then(() => true)
        .catch(() => false);

      if (killedForTimeout) {
        resolve({
          ok: false,
          log: 'Compilation timed out (possible infinite loop or very heavy document).',
        });
        return;
      }

      if (pdfExists) {
        // Read doc.log on success too — it carries the "Output written on
        // doc.pdf (N pages...)" line the caller needs. Fall back to stdout if
        // the log can't be read; never fail the compile over this.
        let successLog = '';
        try {
          successLog = await fs.readFile(path.join(dir, 'doc.log'), 'utf8');
        } catch {
          successLog = stdout;
        }
        resolve({ ok: true, pdfPath, log: successLog });
      } else {
        let log = '';
        try {
          log = await fs.readFile(path.join(dir, 'doc.log'), 'utf8');
        } catch {
          log = stdout + '\n' + stderr;
        }
        resolve({ ok: false, log: log.slice(-MAX_LOG_CHARS) });
      }
    });

    child.on('error', (err) => {
      clearTimeout(timer);
      resolve({ ok: false, log: `Failed to start latexmk: ${err.message}` });
    });
  });
}

// latexmk/pdftex always announce the final page count in the log, e.g.
//   Output written on doc.pdf (2 pages, 123456 bytes).
// Reading it here is free and saves the caller from parsing the PDF just to
// find out how long the document turned out.
function extractPageCount(log) {
  if (!log) return null;
  const m = log.match(/Output written on .*?\((\d+)\s+pages?/i);
  return m ? Number(m[1]) : null;
}

function extractErrors(log) {
  const lines = log.split('\n');
  const errors = [];
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(/^(.+?):(\d+):\s*(.+)$/);
    if (m) {
      errors.push({ file: m[1], line: Number(m[2]), message: m[3] });
      if (errors.length >= 10) break;
    }
  }
  return errors;
}

class LatexService {
  async compileLatex(texPayload, extraFiles = {}, engine = 'pdflatex', templateId = null) {
    const jobID = randomUUID();
    const dir = path.join(os.tmpdir(), 'latex-jobs', jobID);

    await fs.mkdir(dir, { recursive: true });

    try {
      if (templateId) {
        const templatePath = path.join(__dirname, '../templates', templateId);
        try {
          // fs.cp requires Node.js >= 16.7.0
          await fs.cp(templatePath, dir, { recursive: true });
        } catch (err) {
          logger.warn(`Template ${templateId} not found or failed to copy: ${err.message}`);
        }
      }

      await fs.writeFile(path.join(dir, 'doc.tex'), texPayload, 'utf8');

      if (extraFiles && typeof extraFiles === 'object') {
        for (const [filename, content] of Object.entries(extraFiles)) {
          // Prevent directory traversal attacks
          const normalizedPath = path.normalize(filename);
          if (!normalizedPath.startsWith('..') && !path.isAbsolute(normalizedPath)) {
            const targetPath = path.join(dir, normalizedPath);
            await fs.mkdir(path.dirname(targetPath), { recursive: true });
            await fs.writeFile(targetPath, content, 'utf8');
          }
        }
      }

      const compileResult = await runLatexmk(dir, engine);

      if (compileResult.ok) {
        const pdfBuffer = await fs.readFile(compileResult.pdfPath);
        const pageCount = extractPageCount(compileResult.log);
        logger.info({ pageCount }, 'Successfully served t service layer');
        return { success: true, pdfBuffer, pageCount };
      } else {
        const errors = extractErrors(compileResult.log);
        return { success: false, log: compileResult.log, errors };
      }
    } catch (err) {
      logger.error('Error occured in service layer : ', err);
      throw new Error(err.message);
    } finally {
      // Best-effort cleanup
      fs.rm(dir, { recursive: true, force: true }).catch(() => {});
    }
  }
}

module.exports = new LatexService();
