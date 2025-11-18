from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel
from pydantic_yaml import parse_yaml_raw_as, to_yaml_str

from .common import JobSource
from .parser_llm import JobExtraction


class ObsidianFrontMatter(BaseModel):
    created: str  # ISO format datetime
    modified: str  # ISO format datetime
    status: str = "idea"
    company: str | None
    title: str | None
    compensation: str | None
    time_zone: str | None
    location: list[str]
    tech: list[str]
    topics: list[str]
    fit: int
    interest: int
    source_url: str
    source_id: str  # e.g., "hn_comment:123456"


def read_job_notes(input_dir: Path) -> list[JobExtraction]:
    extractions: list[JobExtraction] = []
    for md_file in input_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        if not content.startswith("---"):
            continue
        try:
            _, fm_text, _ = content.split("---", 2)
            fm = parse_yaml_raw_as(ObsidianFrontMatter, fm_text)
        except Exception:
            continue

        extraction = JobExtraction(
            source=JobSource.from_id(fm.source_id, url=fm.source_url),
            company=fm.company,
            title=fm.title,
            compensation=fm.compensation,
            time_zone=fm.time_zone,
            location_tags=fm.location,
            tech_tags=fm.tech,
            topic_tags=fm.topics,
            fit=fm.fit,
            interest=fm.interest,
        )
        extractions.append(extraction)
    return extractions


def write_job_note(
    output_dir: Path,
    extraction: JobExtraction,
    job_text: str,
) -> Path:
    now_iso = datetime.now(timezone.utc).isoformat()
    company = extraction.company or "Unknown"
    safe_name = _safe_filename(company)

    # Disambiguate duplicates by appending counter
    target = output_dir / f"{safe_name}.md"
    idx = 2
    while target.exists():
        target = output_dir / f"{safe_name}-{idx}.md"
        idx += 1

    fm = ObsidianFrontMatter(
        company=extraction.company,
        title=extraction.title,
        created=now_iso,
        modified=now_iso,
        compensation=extraction.compensation,
        time_zone=extraction.time_zone,
        location=extraction.location_tags,
        tech=extraction.tech_tags,
        topics=extraction.topic_tags,
        fit=extraction.fit,
        interest=extraction.interest,
        source_url=extraction.source.url,
        source_id=extraction.source.to_id(),
    )

    yaml_front = to_yaml_str(fm).strip()

    body = (
        f"---\n{yaml_front}\n---\n\n"
        f"# {extraction.company or 'Unknown Company'}\n\n"
        f"Original Posting:\n\n"
        f"````\n{job_text}\n````\n"
    )

    target.write_text(body, encoding="utf-8")
    return target


def _safe_filename(name: str) -> str:
    keep = [c if c.isalnum() or c in ("-", "_", " ") else "-" for c in name]
    cleaned = "".join(keep).strip()
    return cleaned if cleaned else "Empty"
