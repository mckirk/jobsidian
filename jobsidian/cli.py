import argparse
import asyncio
import os
import sys
from pathlib import Path

from .common import JobExtraction, JobSource, JobSourceKind
from .hn_fetcher import fetch_hn_post_comments
from .parser_llm import LLMParser
from .obsidian import read_job_notes, write_job_note


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Obsidian notes from HN 'Who is Hiring' using a CV and an LLM"
    )
    parser.add_argument("--cv", required=True, help="Path to CV text file")
    parser.add_argument("--url", required=True, help="URL to HN 'Who is Hiring' post")
    parser.add_argument(
        "--out",
        default="jobsidian_output",
        help="Output directory for generated Obsidian notes",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENROUTER_MODEL", "openrouter/sherlock-dash-alpha"),
        help="OpenRouter model name (can also set OPENROUTER_MODEL)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=float(os.environ.get("OPENROUTER_TEMPERATURE", 0.1)),
        help="OpenRouter temperature (default 0.1)",
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=100,
        help="Limit number of job postings to process (0 for no limit)",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=400,
        help="Minimum characters to consider a comment a job posting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run extraction without writing files",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.0,
        help="Seconds to sleep between LLM calls (0 for none)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of parallel LLM requests (default 5)",
    )
    return parser.parse_args(argv)


async def process_single_job(
    idx: int,
    jc,
    args,
    cv_text: str,
    existing_ids: set,
    parser: LLMParser,
    out_dir: Path,
    semaphore: asyncio.Semaphore,
) -> tuple[bool, bool, bool]:  # processed, skipped, error
    source = JobSource(
        JobSourceKind.HN_COMMENT,
        url=args.url,
        identifier=jc.comment_id,
        posted_at=jc.posted_at,
    )

    if source.to_id() in existing_ids:
        print(
            f"[{idx}] Skipping already existing job: {source.to_id()}",
            file=sys.stderr,
        )
        return False, True, False

    async with semaphore:
        try:
            extraction: JobExtraction = await parser.extract(
                cv_text=cv_text, job_text=jc.content, job_source=source
            )
        except Exception as e:
            print(f"[{idx}] LLM extraction failed: {e}", file=sys.stderr)
            return False, False, True

    if args.dry_run:
        print(
            f"[{idx}] {extraction.company or 'Unknown Company'} | fit={extraction.fit} interest={extraction.interest} locations={extraction.location_tags} comp={extraction.compensation}",
            file=sys.stderr,
        )
    else:
        write_job_note(
            output_dir=out_dir,
            extraction=extraction,
            job_text=jc.content,
        )
    return True, False, False


async def run_async_processing(
    job_comments, args, cv_text, existing_ids, parser, out_dir
) -> tuple[int, int, int]:
    semaphore = asyncio.Semaphore(args.concurrency)
    tasks = []
    for idx, jc in enumerate(job_comments, start=1):
        tasks.append(
            process_single_job(
                idx, jc, args, cv_text, existing_ids, parser, out_dir, semaphore
            )
        )

    results = await asyncio.gather(*tasks)

    processed = sum(1 for r in results if r[0])
    skipped = sum(1 for r in results if r[1])
    errors = sum(1 for r in results if r[2])

    return processed, skipped, errors


def main(argv: list[str] | None = None) -> int:
    # Load from args.txt, if none given otherwise
    if not argv:
        args_file = Path("args.txt")
        if args_file.exists():
            argv = args_file.read_text(encoding="utf-8").split()

    args = parse_args(argv or sys.argv[1:])

    cv_path = Path(args.cv)
    if not cv_path.exists():
        print(f"CV file not found: {cv_path}", file=sys.stderr)
        return 2
    cv_text = cv_path.read_text(encoding="utf-8", errors="ignore")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Reading existing job notes to avoid duplicates…", file=sys.stderr)
    existing_extractions = read_job_notes(out_dir)
    existing_ids = {extraction.source.to_id() for extraction in existing_extractions}

    print("Fetching HN post…", file=sys.stderr)
    comments = fetch_hn_post_comments(args.url)
    job_comments = [c for c in comments if len(c.content.strip()) >= args.min_chars]
    if not job_comments:
        print(
            "No sufficiently long comments found. Try lowering --min-chars.",
            file=sys.stderr,
        )
        return 1

    if args.max_posts:
        job_comments = job_comments[: args.max_posts]

    print(
        f"Processing {len(job_comments)} postings with model {args.model}…",
        file=sys.stderr,
    )
    parser = LLMParser(
        model=args.model,
        temperature=args.temperature,
        rate_limit_seconds=args.rate_limit,
    )

    processed, skipped, errors = asyncio.run(
        run_async_processing(job_comments, args, cv_text, existing_ids, parser, out_dir)
    )

    print(
        f"Done. Processed={processed} Skipped={skipped} Errors={errors}. Output: {out_dir}",
        file=sys.stderr,
    )
    return 0
