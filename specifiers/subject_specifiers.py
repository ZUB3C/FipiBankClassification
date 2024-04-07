from specifiers.base import BaseSpecifier, Problem

_INFORMATICS_THEME_IDS_2024 = [
    ["2.10", "2.1"],
    ["2.7", "2.6"],
    ["4.5", "1.6"],
    ["2.1", "2.4"],
    ["3.3", "2.9"],
    ["3.3", "2.9"],
    ["2.6", "2.3"],
    ["2.2", "1.3"],
    ["4.2", "2.13"],
    ["4.6", "1.1"],
    ["2.2", "2.3"],
    ["3.3", "1.4"],
    ["1.2", "1.2"],
    ["2.3", "2.5"],
    ["2.7", "2.6"],
    ["3.7", "1.8"],
    ["3.10", "2.12"],
    ["4.5", "2.13"],
    ["2.15", "2.1"],
    ["2.15", "2.1"],
    ["2.15", "2.1"],
    ["1.1", "1.1"],
    ["3.3", "2.11"],
    ["3.9", "2.11"],
    ["3.4", "2.12"],
    ["3.10", "2.12"],
    ["3.2", "3.16", "2.10"],
]

informatics_content_codifier_theme_ids = [
    "2.10",
    "2.7",
    "4.5",
    "2.1",
    "3.3",
    "3.3",
    "2.6",
    "2.2",
    "4.2",
    "4.6",
    "2.2",
    "3.3",
    "1.2",
    "2.3",
    "2.7",
    "3.7",
    "3.10",
    "4.5",
    "2.15",
    "2.15",
    "2.15",
    "1.1",
    "3.3",
    "3.9",
    "3.4",
    "3.10",
    ["3.2", "3.16"],
]
informatics_requirement_codifier_theme_ids = [
    "2.1",
    "2.6",
    "1.6",
    "2.4",
    "2.9",
    "2.9",
    "2.3",
    "1.3",
    "2.13",
    "1.1",
    "2.3",
    "1.4",
    "1.2",
    "2.5",
    "2.6",
    "1.8",
    "2.12",
    "2.13",
    "2.1",
    "2.1",
    "2.1",
    "1.1",
    "2.11",
    "2.11",
    "2.12",
    "2.12",
    "2.10",
]


def _to_list(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return value
    raise ValueError(f"value should be str or list[str], not {type(value)}")


def _format_list(ids: list[str | list[str]]) -> list[list[str]]:
    return [_to_list(i) for i in ids]


informatics_specifier_2024 = BaseSpecifier(
    gia_type="ege",
    subject_name="Информатика и ИКТ",
    year_of_publication=2024,
    problems=[
        Problem(
            exam_number=exam_number,
            content_codifier_theme_ids=content_codifier_theme_ids,
            requirement_codifier_theme_ids=requirement_codifier_theme_ids,
        )
        for exam_number, content_codifier_theme_ids, requirement_codifier_theme_ids in zip(
            range(1, 27 + 1),
            _format_list(informatics_content_codifier_theme_ids),
            _format_list(informatics_requirement_codifier_theme_ids),
        )
    ],
)

if __name__ == "__main__":
    import asyncio

    from database.methods import get_problems_with_details

    gia_type = "ege"
    subject_name = "Информатика и ИКТ"
    for theme_codifier_ids in _INFORMATICS_THEME_IDS_2024:
        for theme_codifier_id in theme_codifier_ids:
            df = asyncio.run(get_problems_with_details(gia_type, subject_name, theme_codifier_id))
            print(df.drop("condition_html", axis=1).to_string())
            exit(0)
    # print(
    #     df[
    #         [
    #             "problem_id",
    #             "url",
    #             "gia_type",
    #             "subject_name",
    #             "theme_codifier_id",
    #         ]
    #     ].to_string()
    # )
