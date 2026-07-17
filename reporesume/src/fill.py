# src/fill.py - Dev B: docxtpl template fill
import json
import os

from docxtpl import DocxTemplate


def fill_template(template_path="cv/cv_template.docx",
                  out_path="output/cv_filled.docx",
                  projects_path="data/projects.json"):
    with open(projects_path, encoding="utf-8") as f:
        projects = json.load(f)

    if not projects:
        raise ValueError("projects.json is empty - refusing to build a CV with no projects.")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    doc = DocxTemplate(template_path)
    # autoescape: data containing & < > must not break the docx XML
    doc.render({"projects": projects}, autoescape=True)
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    print("Wrote", fill_template())
