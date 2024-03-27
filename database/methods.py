from sqlalchemy import select
from sqlalchemy.orm.exc import NoResultFound
from tqdm import tqdm

from database.models import (
    FipiBankProblem,
    FipiBankProblemFile,
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
        for problem_data in problems_data:
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
                select(Subject).filter(Subject.hash == problem_data.subject_hash)
            )
            subject_obj = subject_obj.scalar_one_or_none()
            if subject_obj is None:
                subject_obj = Subject(
                    name=problem_data.subject_name, hash=problem_data.subject_hash
                )
                session.add(subject_obj)
            for theme_data in problem_data.themes:
                if theme_data.codifier_id not in theme_objects:
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
                    theme_objects[theme_data.codifier_id] = theme_obj

        # Creating FipiBankProblem tasks
        for problem_data in tqdm(problems_data, desc="Saving problems to database"):
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
                    gia_types=[gia_type_obj],
                    subjects=[subject_obj],
                    file_urls=[
                        FipiBankProblemFile(file_url=file_url)
                        for file_url in problem_data.file_urls
                    ],
                    themes=[
                        theme_objects[theme_data.codifier_id] for theme_data in problem_data.themes
                    ],
                )
                session.add(problem)

        await session.commit()
