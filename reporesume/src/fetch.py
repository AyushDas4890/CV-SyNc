# src/fetch.py - Dev A: config loading + GitHub API fetching
import base64
import json
import os

import requests
import yaml
from dotenv import load_dotenv

load_dotenv()
API = "https://api.github.com"


def _headers():
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit(
            "GITHUB_TOKEN missing. Create one at https://github.com/settings/tokens "
            "(classic, scope public_repo) and put it in .env"
        )
    return {"Authorization": f"Bearer {token}"}


def parse_repo_ref(ref, default_user=None):
    """Accepts a full GitHub URL, 'owner/name', or bare 'name' (uses default_user).
    Returns (owner, name)."""
    ref = ref.strip().rstrip("/")
    if ref.startswith(("http://", "https://")):
        parts = ref.split("github.com/", 1)
        if len(parts) != 2 or "/" not in parts[1]:
            raise ValueError(f"Not a valid GitHub repo URL: {ref}")
        owner, name = parts[1].split("/")[:2]
        return owner, name.removesuffix(".git")
    if "/" in ref:
        owner, name = ref.split("/", 1)
        return owner, name
    if not default_user:
        raise ValueError(f"Bare repo name '{ref}' needs github_username in config.")
    return default_user, ref


def load_config(path="config/tagged_repos.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if "repos" not in cfg or not cfg["repos"]:
        raise ValueError("Config has no repos listed - nothing to do.")
    default_user = cfg.get("github_username")
    normalized = []
    for entry in cfg["repos"]:
        if isinstance(entry, str):  # allow plain URL/name lines in YAML
            entry = {"name": entry}
        ref = entry.get("url") or entry.get("name")
        if not ref:
            raise ValueError(f"Repo entry missing 'name' or 'url': {entry}")
        owner, name = parse_repo_ref(ref, default_user)
        normalized.append({"owner": owner, "name": name,
                           "notes": entry.get("notes", "") or ""})
    cfg["repos"] = normalized
    return cfg


def fetch_repo(user, repo_name):
    headers = _headers()
    r = requests.get(f"{API}/repos/{user}/{repo_name}", headers=headers, timeout=30)
    if r.status_code == 401:
        raise SystemExit("GitHub returned 401 - token is wrong or .env not loading.")
    if r.status_code == 404:
        raise SystemExit(f"Repo {user}/{repo_name} not found - check the name in tagged_repos.yaml")
    r.raise_for_status()
    info = r.json()

    langs = requests.get(
        f"{API}/repos/{user}/{repo_name}/languages", headers=headers, timeout=30
    ).json()

    readme_resp = requests.get(
        f"{API}/repos/{user}/{repo_name}/readme", headers=headers, timeout=30
    )
    if readme_resp.status_code == 200:
        readme = base64.b64decode(readme_resp.json()["content"]).decode(
            "utf-8", errors="replace"
        )
    else:
        readme = ""  # repo has no README - handle gracefully

    return {
        "name": repo_name,
        "description": info.get("description") or "",
        "topics": info.get("topics", []),
        "languages": list(langs.keys()),
        "readme": readme,
        "url": info["html_url"],
    }


def fetch_all(cfg, raw_dir="data/raw"):
    os.makedirs(raw_dir, exist_ok=True)
    results = []
    for repo in cfg["repos"]:
        owner = repo.get("owner") or cfg.get("github_username")
        print(f"Fetching {owner}/{repo['name']} ...")
        raw = fetch_repo(owner, repo["name"])
        raw["notes"] = repo.get("notes", "") or ""
        with open(os.path.join(raw_dir, f"{repo['name']}.json"), "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2)
        results.append(raw)
    return results


if __name__ == "__main__":
    cfg = load_config()
    print(f"Found {len(cfg['repos'])} tagged repos for user {cfg['github_username']}")
    fetch_all(cfg)
    print("Raw repo data saved to data/raw/")
