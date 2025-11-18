from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class JobSourceKind(Enum):
    HN_COMMENT = "hn_comment"


@dataclass
class JobSource:
    kind: JobSourceKind
    url: str
    identifier: str  # e.g., comment ID
    posted_at: str | None  # ISO format datetime

    def to_id(self) -> str:
        return f"{self.kind.value}:{self.identifier}"

    @classmethod
    def from_id(cls, id_str: str, url: str, posted_at: str | None) -> "JobSource":
        kind_str, identifier = id_str.split(":", 1)
        kind = JobSourceKind(kind_str)
        return cls(kind=kind, url=url, identifier=identifier, posted_at=posted_at)


@dataclass
class JobExtraction:
    source: JobSource
    company: Optional[str]
    compensation: Optional[str]
    time_zone: Optional[str]
    location_tags: List[str]
    tech_tags: List[str]
    topic_tags: List[str]
    fit: int
    interest: int
    title: Optional[str] = None
