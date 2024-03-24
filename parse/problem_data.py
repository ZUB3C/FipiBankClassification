from __future__ import annotations

from typing import NamedTuple


class ProblemData(NamedTuple):
    problem_id: str
    subject_name: str
    subject_hash: str
    url: str
    condition_html: str
    gia_type: str
    file_urls: list[str]
