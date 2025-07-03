from dataclasses import dataclass


@dataclass
class Problem:
    exam_number: int
    content_codifier_theme_ids: list[
        str
    ]  # Коды проверяемых элементов содержания (по кодификатору)
    requirement_codifier_theme_ids: list[str]  # Коды проверяемых требований (по кодификатору)


@dataclass
class BaseSpecifier:
    gia_type: str
    subject_name: str
    year_of_publication: int
    problems: list[Problem]
