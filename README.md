Jobsidian – HN 'Who is Hiring' to Obsidian notes
================================================

Generate Obsidian-ready Markdown notes for each job posting in a Hacker News 'Who is Hiring' thread, enriched with structured properties extracted by an LLM using your CV.

Quick start
----------

1) Install dependencies

```bash
pip install -e .
```

2) Set your OpenRouter key

```bash
export OPENROUTER_API_KEY=sk-...
```

3) Prepare inputs

- CV file: plain text version of your CV (e.g., exported from your doc).  
- HN URL: link to a 'Who is Hiring' post (e.g., https://news.ycombinator.com/item?id=XXXXXXX).

4) Run

```bash
jobsidian --cv /path/to/cv.txt --url https://news.ycombinator.com/item?id=XXXXXXX --out ./obsidian-jobs
```

Options
-------

- `--model`: OpenRouter model (default from `OPENROUTER_MODEL` or `openrouter/sherlock-dash-alpha`).
- `--temperature`: Sampling temperature (default 0.1).
- `--max-posts`: Limit number of comments to process (default 100).
- `--min-chars`: Heuristic to identify job posts by length (default 400).
- `--dry-run`: Print extractions without writing files.
- `--rate-limit`: Seconds to sleep between LLM calls.

Output
------

Each note has YAML frontmatter with:

- `company`: Company name (string)
- `title`: Job title (string or null)
- `created` / `modified`: ISO timestamps
- `compensation`: Free-text compensation
- `location`: Array of tags (e.g., `["berlin", "hybrid"]` or `["nyc", "sf"]`)
- `fit`: 1–5
- `interest`: 1–5
- `source`: HN post URL
- `hn_comment_id`: HN comment id, if available

Notes
-----

- Requires network access to fetch the HN page and OpenRouter API access for extraction.
- Obsidian recognizes YAML frontmatter; you can create views and filters based on these properties.
- For testing without writing files, use `--dry-run`.

