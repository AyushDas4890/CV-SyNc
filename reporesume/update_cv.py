# update_cv.py - the single command that runs everything
import argparse
import json

from src.fetch import load_config, fetch_all, parse_repo_ref
from src.summarize import summarize_repo, _client
from src.fill import fill_template
from src.convert import docx_to_pdf
from src.review import review_and_confirm


def main():
    ap = argparse.ArgumentParser(description="Regenerate CV from tagged GitHub repos")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch + summarize only; do not touch the CV")
    ap.add_argument("--skip-fetch", action="store_true",
                    help="reuse existing data/projects.json (no API calls)")
    ap.add_argument("--repo", action="append", default=[], metavar="URL",
                    help="GitHub repo link (or owner/name); repeatable. "
                         "Overrides the config file list. "
                         "Append '::notes text' to attach notes, e.g. "
                         "--repo https://github.com/u/r::'91%% accuracy'")
    args = ap.parse_args()

    if not args.skip_fetch:
        cfg = load_config()
        if args.repo:  # user-provided links replace the config list
            repos = []
            for ref in args.repo:
                notes = ""
                if "::" in ref:
                    ref, notes = ref.split("::", 1)
                owner, name = parse_repo_ref(ref, cfg.get("github_username"))
                repos.append({"owner": owner, "name": name, "notes": notes})
            cfg["repos"] = repos
        raws = fetch_all(cfg)
        client = _client()
        projects = []
        for raw in raws:
            print(f"Summarizing {raw['name']} ...")
            result = summarize_repo(raw, client)
            if result:
                projects.append(result)
        with open("data/projects.json", "w", encoding="utf-8") as f:
            json.dump(projects, f, indent=2)
        print(f"Wrote {len(projects)} projects to data/projects.json")

    if args.dry_run:
        print("Dry run - stopping before template fill.")
        return

    filled = fill_template()          # docxtpl - template preserved
    if review_and_confirm(filled):    # human gate
        pdf = docx_to_pdf(filled)     # LibreOffice conversion
        print("Saved", pdf)


if __name__ == "__main__":
    main()
