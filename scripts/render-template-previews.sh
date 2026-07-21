#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

# Renders every page of each CV template's sample .tex as PNGs into
# frontend/public/template-previews/, plus a manifest.json of page counts.
# Requires: pdflatex, xelatex, pdftoppm (poppler-utils) on PATH.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATES_DIR="$ROOT_DIR/cv-templates"
OUT_DIR="$ROOT_DIR/frontend/public/template-previews"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

mkdir -p "$OUT_DIR"

# id:engine:main.tex (relative to cv-templates/<id>/)
TEMPLATES=(
  "jake:pdflatex:main.tex"
)

for entry in "${TEMPLATES[@]}"; do
  id="${entry%%:*}"
  rest="${entry#*:}"
  engine="${rest%%:*}"
  main_tex="${rest#*:}"

  src_dir="$TEMPLATES_DIR/$id"
  job_dir="$WORK_DIR/$id"
  mkdir -p "$job_dir"
  cp -r "$src_dir"/. "$job_dir"/

  echo "== $id ($engine) =="
  if ! (cd "$job_dir" && "$engine" -interaction=nonstopmode -halt-on-error "$main_tex" > "$job_dir/build.log" 2>&1); then
    echo "ERROR compiling $id — last 40 lines of build.log:" >&2
    tail -n 40 "$job_dir/build.log" >&2
    exit 1
  fi

  pdf_name="$(basename "$main_tex" .tex).pdf"
  pdftoppm -png -r 150 "$job_dir/$pdf_name" "$job_dir/page"

  mapfile -t pages < <(printf '%s\n' "$job_dir"/page-*.png | sort -V)
  page_count=${#pages[@]}
  echo "$id: $page_count page(s)"

  # page-1.png -> <id>.png, page-2.png -> <id>-p2.png, ...
  n=1
  for f in "${pages[@]}"; do
    if [ "$n" -eq 1 ]; then
      cp "$f" "$OUT_DIR/$id.png"
    else
      cp "$f" "$OUT_DIR/$id-p$n.png"
    fi
    n=$((n + 1))
  done
done
