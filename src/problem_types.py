from dataclasses import dataclass


@dataclass
class ThemeData:
    codifier_id: str
    name: str


@dataclass
class ProblemData:
    problem_id: str
    subject_name: str
    subject_hash: str
    url: str
    condition_html: str
    gia_type: str
    file_urls: list[str]
    themes: list[ThemeData]
