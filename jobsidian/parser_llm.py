from __future__ import annotations

import time
import os
from pydantic import BaseModel

from openrouter import OpenRouter
from openrouter.components import ResponseFormatJSONSchema, JSONSchemaConfig

from .common import JobExtraction, JobSource


class LLMAnswer(BaseModel):
    company: str | None
    compensation: str | None
    time_zone: str | None
    location_tags: list[str]
    tech_tags: list[str]
    topic_tags: list[str]
    fit: int
    interest: int
    title: str | None

    def normalize(self):
        self.location_tags = _normalize_tags(self.location_tags)
        self.tech_tags = _normalize_tags(self.tech_tags)
        self.topic_tags = _normalize_tags(self.topic_tags)
        self.fit = _clamp_int(self.fit, 1, 5, 1)
        self.interest = _clamp_int(self.interest, 1, 5, 1)
        self.company = _norm_str(self.company)
        self.compensation = _norm_str(self.compensation)
        self.time_zone = _norm_str(self.time_zone)
        self.title = _norm_str(self.title)


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

    async def extract(
        self, cv_text: str, job_text: str, job_source: JobSource
    ) -> JobExtraction:
        if self.rate_limit_seconds > 0:
            time.sleep(self.rate_limit_seconds)

        system = (
            "You are an assistant that extracts structured data from job postings and evaluates fit and interest. "
            "Respond ONLY with a compact JSON object matching the required schema. Keep tag tokens consistent with the provided prior tag inventory; reuse existing tokens when applicable and avoid near-duplicate variants."
        )

        user = (
            "Extract fields from the job posting and evaluate against the CV.\n\n"
            "Return a JSON object with keys: \n"
            "- company: string | null (verbatim as in the text)\n"
            "- compensation: string | null (free text as seen)\n"
            "- time_zone: string | null (if specified, can be a range)\n"
            "- location_tags: array of strings (lowercase simple tags, e.g., ['berlin','hybrid'] or ['nyc','sf'])\n"
            "- tech_tags: array of strings (lowercase simple tags for relevant technologies, e.g., ['python','aws','docker'])\n"
            "- topic_tags: array of strings (lowercase simple tags for relevant topics/fields, e.g., ['ai','web3','formal-methods'])\n"
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

        resp = await self.client.chat.send_async(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
            response_format=ResponseFormatJSONSchema(
                json_schema=JSONSchemaConfig(
                    name="LLMAnswer", schema_=LLMAnswer.model_json_schema()
                )
            ),
        )
        content = resp.choices[0].message.content

        if not isinstance(content, str):
            raise ValueError("LLM response content is not a string")

        data = LLMAnswer.model_validate_json(content)
        data.normalize()

        extraction = JobExtraction(
            company=data.company,
            compensation=data.compensation,
            time_zone=data.time_zone,
            location_tags=data.location_tags,
            tech_tags=data.tech_tags,
            topic_tags=data.topic_tags,
            fit=data.fit,
            interest=data.interest,
            title=data.title,
            source=job_source,
        )

        return extraction


def _normalize_tags(tags: list[str]) -> list[str]:
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


def _norm_str(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None
