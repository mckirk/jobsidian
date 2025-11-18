Jobsidian – Turn HN "Who is Hiring" Threads into Enriched Obsidian Notes
=======================================================================

Jobsidian fetches a Hacker News "Who is Hiring" thread, filters likely job postings, sends each through an LLM together with your CV, and emits Obsidian‑ready Markdown notes. Each note includes rich YAML frontmatter (company, title, tags, fit & interest scores, etc.) enabling filtering, dataview queries, and prioritization inside your Obsidian vault.

Why?
----
Manually triaging large monthly HN job threads is slow and ad‑hoc. Jobsidian accelerates this by:

* Extracting normalized tags (location, tech, topics).
* Scoring subjective "fit" and "interest" (1–5) for rapid prioritization (LLM heuristic – always manually review).
* Avoiding duplicate processing by reading existing notes in the output directory.
* Generating consistent filenames and frontmatter usable by Obsidian plugins.

Quick Start
-----------

Create / activate a Python 3.11+ environment, then install.

```bash
# Using uv (fast resolver) – recommended
uv pip install -e .

# Or classic pip
pip install -e .
```

Set your OpenRouter API key (required for LLM extraction). You may also place it in a `.env` file if you run via `python main.py` (which loads dotenv). The installed `jobsidian` console script does NOT auto-load `.env`.

```bash
export OPENROUTER_API_KEY=sk-...
```

Optional environment overrides:

```bash
export OPENROUTER_MODEL="openrouter/sherlock-dash-alpha"   # or another supported model
export OPENROUTER_TEMPERATURE=0.1                           # numeric string
```

Prepare inputs:

* CV file: plain text version of your CV (export or copy/paste – minimal formatting).
* HN URL: the monthly thread link, e.g. https://news.ycombinator.com/item?id=XXXXXXX

Run:

```bash
jobsidian --cv /path/to/cv.txt \
		  --url https://news.ycombinator.com/item?id=XXXXXXX \
		  --out ./obsidian-jobs
```

CLI Options
-----------

| Flag | Description | Default |
|------|-------------|---------|
| `--cv` | Path to CV plain‑text file | (required) |
| `--url` | HN "Who is Hiring" post URL | (required) |
| `--out` | Output directory for notes | `jobsidian_output` |
| `--model` | OpenRouter model name | `OPENROUTER_MODEL` env or `openrouter/sherlock-dash-alpha` |
| `--temperature` | Sampling temperature | `0.1` (or `OPENROUTER_TEMPERATURE`) |
| `--max-posts` | Max job comments to process | `100` |
| `--min-chars` | Minimum comment length to treat as job | `400` |
| `--dry-run` | Skip writing files, print summary lines | off |
| `--rate-limit` | Sleep seconds between LLM calls | `0.0` |

Convenience: `args.txt`
-----------------------
If you create an `args.txt` file in the project root, Jobsidian will read arguments from it when invoked without explicit CLI parameters. Example contents:

```
--cv ./cv.txt --url https://news.ycombinator.com/item?id=XXXXXXX --out ./obsidian-jobs --max-posts 50
```

Output Structure
----------------
Each generated Markdown file includes YAML frontmatter (parsed/rewritten on subsequent runs to avoid duplicates). Example:

```yaml
---
created: 2025-11-18T12:34:56.789012+00:00
modified: 2025-11-18T12:34:56.789012+00:00
status: idea
company: Acme Robotics
title: Senior Python Engineer
compensation: Competitive + equity
location: ["remote", "eu"]
tech: ["python", "aws", "docker"]
topics: ["ml", "infrastructure"]
fit: 4
interest: 5
source_url: https://news.ycombinator.com/item?id=XXXXXXX
source_id: hn_comment:123456
---
```

Below the frontmatter the original posting content is preserved in a fenced block for search/reference.

Duplicate Handling
------------------
Jobsidian scans existing `.md` files in the output directory, reconstructs their `source_id` values, and skips re‑processing any previously extracted comments.

Tag Extraction & Normalization
------------------------------
Location (`location`), technology (`tech`), and topic (`topics`) tags are normalized to lowercase tokens (no punctuation). This keeps queries simple in Obsidian plugins (e.g. Dataview).

Scoring Heuristics
------------------
`fit` and `interest` are LLM‑generated integers (1–5). Treat them as a starting point; always manually validate. You can edit scores directly in Obsidian—Jobsidian will retain them.

Running With .env
-----------------
If you prefer, create a `.env` file with:

```
OPENROUTER_API_KEY=sk-...
OPENROUTER_MODEL=openrouter/sherlock-dash-alpha
OPENROUTER_TEMPERATURE=0.1
```

Then run via:

```bash
python main.py --cv ./cv.txt --url https://news.ycombinator.com/item?id=XXXXXXX
```

Development
-----------
* Code style is minimal; feel free to submit PRs for enhancements.
* Uses `openrouter` SDK and `pydantic` for frontmatter models.
* Tested against standard HN thread structures; edge cases (deleted comments, unusual formatting) may need refinement.

Limitations & Future Ideas
--------------------------
* Single source (HN comments) – could add other feeds.
* No batching; one API call per job comment (add concurrency or cost controls).
* Potential LLM hallucinations in tags/compensation – manual review recommended.
* Could add a re‑ranking step or embeddings for semantic search.

License
-------
MIT

Disclaimer
----------
LLM outputs may be inaccurate. Always verify before acting on the extracted data.

