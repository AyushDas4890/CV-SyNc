# src/review.py - Dev B: diff + human review gate
import difflib
import os

from docx import Document

SNAPSHOT = "output/last_approved.txt"


def docx_text(path):
    return "\n".join(p.text for p in Document(path).paragraphs if p.text)


def review_and_confirm(filled_docx, assume_yes=False):
    new_text = docx_text(filled_docx)
    old_text = ""
    if os.path.exists(SNAPSHOT):
        with open(SNAPSHOT, encoding="utf-8") as f:
            old_text = f.read()

    changes = list(difflib.unified_diff(
        old_text.splitlines(), new_text.splitlines(),
        fromfile="current CV", tofile="proposed CV", lineterm=""))
    if not changes:
        print("No changes detected.")
        return False

    print("\n".join(changes))
    if assume_yes:
        answer = "y"
    else:
        answer = input("\nApply these changes? [y/N] ").strip().lower()
    if answer == "y":
        with open(SNAPSHOT, "w", encoding="utf-8") as f:
            f.write(new_text)
        return True
    print("Aborted - CV not modified.")
    return False
