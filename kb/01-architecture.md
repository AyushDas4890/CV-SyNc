# Architecture

4 services, Node/Express assumed everywhere (match teammate).

```
user → [auth svc] session cookie guards all APIs
user pick repos → [fetch+LLM svc] → data/projects.json
projects.json + cv_template.tex → [writer svc] → final .tex + diff gate
final .tex → POST compiler /api/compile → PDF (or 422 errors)
```

Contracts:
1. projects.json (LLM half → writer half):
```json
[{"title":"...","tech_stack":["..."],"bullets":["..."],"repo_url":"...","dates":"..."}]
```
2. compiler API: POST /api/compile {tex:string} → 200 PDF binary | 422 {ok,log,errors:[{file,line,message}]} | 400 missing | 413 >2M chars.
3. writer API (planned): POST /api/write {projects} (?dry=true → diff only), POST /api/approve → compile + snapshot.

Infra: docker-compose = auth + writer + compiler + mysql + redis. Reverse proxy (nginx) in front, single public port — deploy config, not app code.

Key principle: LLM outputs JSON ONLY, never raw LaTeX. Deterministic renderer owns tex. Diff gate between LLM and CV always.
