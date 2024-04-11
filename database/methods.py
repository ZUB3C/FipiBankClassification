import asyncio

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.orm.exc import NoResultFound
from tqdm import tqdm

from database.models import (
    FipiBankProblem,
    FipiBankProblemCodifierTheme,
    FipiBankProblemFile,
    FipiBankProblemGiaType,
    FipiBankProblemSubject,
    GiaType,
    Subject,
    Theme,
    async_session,
)
from parse.problem_data import ProblemData


async def save_subject_problems(problems_data: list[ProblemData]) -> None:
    async with async_session() as session, session.begin():
        # Creating or retrieving theme objects from the database
        theme_objects = {}
        for problem_data in tqdm(problems_data, desc="Saving problems to database"):
            # Creating or retrieving gia_type object from the database
            gia_type_obj = (
                await session.execute(
                    select(GiaType).filter(GiaType.name == problem_data.gia_type)
                )
            ).scalar_one_or_none()
            if gia_type_obj is None:
                gia_type_obj = GiaType(name=problem_data.gia_type)
                session.add(gia_type_obj)

            # Creating or retrieving subject object from the database
            subject_obj = await session.execute(
                select(Subject).filter(Subject.name == problem_data.subject_name)
            )
            subject_obj = subject_obj.scalar_one_or_none()
            if subject_obj is None:
                subject_obj = Subject(
                    name=problem_data.subject_name, hash=problem_data.subject_hash
                )
                session.add(subject_obj)
            for theme_data in problem_data.themes:
                if (theme_data.codifier_id, problem_data.subject_hash) not in theme_objects:
                    theme_obj = await session.execute(
                        select(Theme)
                        .filter(Theme.codifier_id == theme_data.codifier_id)
                        .filter(Theme.subject_id == subject_obj.id)
                    )
                    theme_obj = theme_obj.scalar_one_or_none()
                    if theme_obj is None:
                        theme_obj = Theme(
                            codifier_id=theme_data.codifier_id,
                            subject_id=subject_obj.id,
                            name=theme_data.name,
                        )
                        session.add(theme_obj)
                    theme_objects[(theme_data.codifier_id, problem_data.subject_hash)] = theme_obj
            try:
                (
                    await session.execute(
                        select(FipiBankProblem).filter(
                            FipiBankProblem.problem_id == problem_data.problem_id
                        )
                    )
                ).scalar_one()
                continue
            except NoResultFound:
                problem = FipiBankProblem(
                    problem_id=problem_data.problem_id,
                    url=problem_data.url,
                    condition_html=problem_data.condition_html,
                    gia_type=[gia_type_obj],
                    subject=[subject_obj],
                    file_urls=[
                        FipiBankProblemFile(file_url=file_url)
                        for file_url in problem_data.file_urls
                    ],
                    themes=[
                        theme_objects[(theme_data.codifier_id, problem_data.subject_hash)]
                        for theme_data in problem_data.themes
                    ],
                )
                session.add(problem)

        await session.commit()


async def get_problems_with_details(
    gia_type: str, subject_name: str, content_codifier_theme_id: str
) -> pd.DataFrame:
    async with async_session() as session:
        stmt = (
            select(
                FipiBankProblem.problem_id,
                FipiBankProblem.url,
                FipiBankProblem.condition_html,
            )
            .select_from(
                FipiBankProblem.__table__.join(FipiBankProblemGiaType)
                .join(GiaType)
                .join(FipiBankProblemSubject)
                .join(Subject)
                .join(FipiBankProblemCodifierTheme)
                .join(Theme)
            )
            .where(
                GiaType.name == gia_type,
                Subject.name == subject_name,
                Theme.codifier_id == content_codifier_theme_id,
                FipiBankProblem.exam_number == None,  # noqa: E711
            )
            .where(Subject.name == subject_name)
        )

        result = await session.execute(stmt)
        rows = result.fetchall()

        return pd.DataFrame(rows, columns=result.keys())


async def get_subject_problems(gia_type: str, subject_name: str) -> pd.DataFrame:
    async with async_session() as session:
        stmt = (
            select(
                FipiBankProblem.problem_id,
                FipiBankProblem.url,
                FipiBankProblem.condition_html,
            )
            .select_from(
                FipiBankProblem.__table__.join(FipiBankProblemGiaType)
                .join(GiaType)
                .join(FipiBankProblemSubject)
                .join(Subject)
            )
            .where(
                GiaType.name == gia_type,
                Subject.name == subject_name,
            )
            .where(Subject.name == subject_name)
        )

        result = await session.execute(stmt)
        rows = result.fetchall()

        return pd.DataFrame(rows, columns=result.keys())


async def get_problems_by_exam_number(exam_number: int) -> list[str]:
    async with async_session() as session:
        return (
            (
                await session.execute(
                    select(FipiBankProblem.condition_html).where(
                        FipiBankProblem.exam_number == exam_number
                    )
                )
            )
            .scalars()
            .all()
        )


async def add_exam_number_to_problems(problem_ids: list[str], exam_number: int | None) -> None:
    async with async_session() as session:
        try:
            problems = await session.execute(
                select(FipiBankProblem).filter(FipiBankProblem.problem_id.in_(problem_ids))
            )
            problems = problems.scalars().all()

            for problem in problems:
                problem.exam_number = exam_number

            await session.commit()
        except NoResultFound:
            print("No FipiBank problems found with provided IDs.")


async def delete_exam_numbers():
    async with async_session() as session:
        stmt = update(FipiBankProblem).values({FipiBankProblem.exam_number: None})
        await session.execute(stmt)
        await session.commit()


if __name__ == "__main__":
    # df = asyncio.run(get_subject_problems(gia_type="ege", subject_name="Информатика и ИКТ"))
    # print(len(df))
    print(len(asyncio.run(get_problems_with_details("ege", "Информатика и ИКТ", "2.10"))))
