# src/summarize.py - Dev A: LLM summarization (OpenAI SDK)
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

PROMPT = """You are a resume writing assistant. Given data about a GitHub
repository, produce resume content for it.

Repository name: {name}
Languages: {languages}
Topics: {topics}
Description: {description}
Human-provided notes (must be included if present): {notes}
README:
{readme}

Reply with ONLY a JSON object, no other text, in exactly this shape:
{{
  "title": "Human-readable project title",
  "tech_stack": ["list", "of", "technologies"],
  "bullets": ["2-3 resume bullets, each starting with an action verb,",
              "each under 25 words, using notes metrics if provided"]
}}"""

EMPTY_README_HINT = (
    "\nNOTE: The README is missing or very short. Rely on the description, "
    "topics, languages and notes instead."
)


def _client():
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY missing from .env")
    return OpenAI()


def _call_llm(client, prompt):
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.choices[0].message.content.strip()
    if text.startswith("```"):  # strip markdown fences if any
        text = text.strip("`").lstrip("json").strip()
    return json.loads(text)  # raises if the model misbehaved


def summarize_repo(raw, client=None):
    client = client or _client()
    prompt = PROMPT.format(
        name=raw["name"],
        languages=", ".join(raw["languages"]),
        topics=", ".join(raw.get("topics", [])),
        description=raw["description"],
        notes=raw.get("notes", ""),
        readme=raw["readme"][:6000],  # cap length to control cost
    )
    if len(raw["readme"]) < 100:
        prompt += EMPTY_README_HINT

    data = None
    for attempt in (1, 2):  # retry once on bad JSON
        try:
            data = _call_llm(client, prompt)
            break
        except (json.JSONDecodeError, ValueError) as e:
            if attempt == 2:
                print(f"WARNING: skipping {raw['name']} - LLM output invalid twice ({e})")
                return None

    # Validate the contract before accepting it
    for key in ("title", "tech_stack", "bullets"):
        if key not in data:
            print(f"WARNING: skipping {raw['name']} - LLM output missing key: {key}")
            return None
    data["repo_url"] = raw["url"]
    return data


def summarize_all(raw_dir="data/raw", out_path="data/projects.json"):
    client = _client()
    projects = []
    for fname in sorted(os.listdir(raw_dir)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(raw_dir, fname), encoding="utf-8") as f:
            raw = json.load(f)
        print(f"Summarizing {raw['name']} ...")
        result = summarize_repo(raw, client)
        if result:
            projects.append(result)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2)
    print(f"Wrote {len(projects)} projects to {out_path}")
    return projects


if __name__ == "__main__":
    summarize_all()
