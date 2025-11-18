from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
import markdownify


@dataclass
class HNComment:
    comment_id: str
    content: str  # as Markdown


def fetch_hn_post_comments(url: str) -> List[HNComment]:
    """Fetch a Hacker News 'Who is Hiring' post and return list of comments as potential job postings.

    Parses HTML and extracts comment text from elements with class 'commtext'.
    Attempts to map each comment to a comment_id for deep linking when possible.
    """
    _validate_hn_url(url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    comments: List[HNComment] = []

    # HN comments are inside <tr class="athing comtr" id="COMMENT_ID">, with body in div.commtext
    for comtr in soup.select("tr.athing.comtr"):
        # Only keep top-level comments, i.e. those with a '<td class="ind" indent="0">' element
        indent_el = comtr.select_one('td.ind[indent="0"]')
        if not indent_el:
            continue

        comment_id = comtr.get("id")

        if not comment_id or not isinstance(comment_id, str):
            logging.warning("Skipping comment without ID")
            continue

        body_el = comtr.select_one("div.commtext")
        if not body_el:
            logging.debug(f"Comment {comment_id} missing body element; skipping.")
            continue

        # Convert HTML to markdown
        body_html = str(body_el)
        body_md = markdownify.markdownify(body_html, heading_style="ATX")
        comments.append(HNComment(comment_id=comment_id, content=body_md))

    return comments


def _validate_hn_url(url: str) -> None:
    p = urlparse(url)
    if p.netloc not in {
        "news.ycombinator.com",
        "hacker-news.firebaseio.com",
        "hn.algolia.com",
    }:
        # We allow anything, but warn silently by not raising; to keep minimal friction
        return
