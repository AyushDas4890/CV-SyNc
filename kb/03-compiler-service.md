# Compiler service — CV_BUILDER (teammate Abhinav, DONE)

Repo: https://github.com/IamAbhinav01/CV_BUILDER
Node/Express MVC: router → controller → service. Overleaf-like: tex in, PDF out.

API:
- GET /api/health → {ok:true}
- POST /api/compile {tex:string} → 200 PDF binary (Content-Type: application/pdf) | 422 {ok:false, log, errors:[{file,line,message}] max 10, regex `^(.+?):(\d+):\s*(.+)$`} | 400 tex missing | 413 tex >2_000_000 chars. Body limit 5mb.

Internals:
- UUID job dir os.tmpdir()/latex-jobs/<uuid>/ → write doc.tex → spawn latexmk args: -pdf -interaction=nonstopmode -halt-on-error -no-shell-escape -file-line-error -outdir
- env openin_any=p openout_any=p (paranoid file access = sandbox)
- timeout SIGKILL — code 15000ms (README wrongly says 30s)
- fail → read doc.log, last 20000 chars, extract errors
- finally: rm -rf job dir

Docker: minidocks/texlive:2023-medium + tlmgr install latexmk preprint titlesec marvosym enumitem fancyhdr babel-english hyphen-english + node. Port 3000.

KNOWN BUGS (relay to teammate):
1. COMPILE_TIMEOUT_MS=15000 but README claims 30s — align
2. server.config.js: PORT no fallback → undefined without .env (docker sets it, bare npm run dev crashes). Fix: `process.env.PORT || 3000`

CONSTRAINT for writer svc: only packages in that Docker image compile. Unknown \usepackage = 422. Jake template packages all present in tlmgr list above + texlive medium.
