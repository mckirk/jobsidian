from __future__ import annotations

from enum import Enum
import json
import time
import os
from dataclasses import dataclass
from typing import List, Optional

from openrouter import OpenRouter

from .common import JobExtraction, JobSource


class LLMParser:
    def __init__(
        self, model: str, temperature: float = 0.1, rate_limit_seconds: float = 0.0
    ):
        self.model = model
        self.temperature = temperature
        self.rate_limit_seconds = rate_limit_seconds
        self.client = OpenRouter(
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    def extract(
        self, cv_text: str, job_text: str, job_source: JobSource
    ) -> JobExtraction:
        if self.rate_limit_seconds > 0:
            time.sleep(self.rate_limit_seconds)

        system = (
            "You are an assistant that extracts structured data from job postings and evaluates fit and interest. "
            "Respond ONLY with a compact JSON object matching the required schema."
        )

        user = (
            "Extract fields from the job posting and evaluate against the CV.\n\n"
            "Return a JSON object with keys: \n"
            "- company: string | null (verbatim as in the text)\n"
            "- compensation: string | null (free text as seen)\n"
            "- location_tags: array of strings (lowercase simple tags, e.g., ['berlin','hybrid'] or ['nyc','sf'])\n"
            "- tech_tags: array of strings (lowercase simple tags for relevant technologies, e.g., ['python','aws','docker'])\n"
            "- topic_tags: array of strings (lowercase simple tags for relevant topics/fields, e.g., ['ml','web','mobile'])\n"
            "- fit: integer 1-5 (higher means better fit)\n"
            "- interest: integer 1-5 (higher means more interesting to the candidate)\n"
            "- title: string | null (job title if identifiable; comma-separated list if multiple jobs included)\n\n"
            "Rules:\n"
            "- Use only integers for fit and interest.\n"
            "- If uncertain, infer conservatively and return a lower bound; high values in fit and interest should remain rare to provide a clear signal.\n"
            "- location_tags should be short, normalized tokens: lowercase, no punctuation; split multiple locations separately.\n"
            f"CV:\n---\n{cv_text}\n---\n\n"
            f"JOB POSTING:\n---\n{job_text}\n---\n"
        )

        resp = self.client.chat.send(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content

        if not isinstance(content, str):
            raise ValueError("LLM response content is not a string")

        data = json.loads(content)

        company = _norm_str(data.get("company"))
        compensation = _norm_str(data.get("compensation"))
        title = _norm_str(data.get("title"))
        fit = _clamp_int(data.get("fit"), 1, 5, default=3)
        interest = _clamp_int(data.get("interest"), 1, 5, default=3)
        loc_tags = data.get("location_tags") or []
        if not isinstance(loc_tags, list):
            loc_tags = []
        loc_tags = _normalize_tags(loc_tags)
        tech_tags = data.get("tech_tags") or []
        if not isinstance(tech_tags, list):
            tech_tags = []
        tech_tags = _normalize_tags(tech_tags)
        topic_tags = data.get("topic_tags") or []
        if not isinstance(topic_tags, list):
            topic_tags = []
        topic_tags = _normalize_tags(topic_tags)

        return JobExtraction(
            company=company,
            compensation=compensation,
            location_tags=loc_tags,
            tech_tags=tech_tags,
            topic_tags=topic_tags,
            fit=fit,
            interest=interest,
            title=title,
            source=job_source,
        )


def _normalize_tags(tags: List[str]) -> List[str]:
    out = []
    for t in tags:
        if not isinstance(t, str):
            continue
        cleaned = (t or "").strip().lower()
        if not cleaned:
            continue
        if cleaned not in out:
            out.append(cleaned)
    return out


def _clamp_int(val, lo: int, hi: int, default: int) -> int:
    try:
        n = int(val)
    except Exception:
        return default
    return max(lo, min(hi, n))


def _norm_str(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None
