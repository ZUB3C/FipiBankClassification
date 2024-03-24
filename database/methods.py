from sqlalchemy import select
from sqlalchemy.orm.exc import NoResultFound

from database.models import (
    FipiBankProblem,
    FipiBankProblemFile,
    GiaType,
    Subject,
    async_session,
)
from parse.problem_data import ProblemData

_GIA_TYPE_STR_TO_ID: dict[str, int] = {"oge": 0, "ege": 1}


async def add_problem_to_db(problem_data: ProblemData):
    async with async_session() as session, session.begin():
        try:
            (
                await session.execute(
                    select(FipiBankProblem).filter(
                        FipiBankProblem.problem_id == problem_data.problem_id
                    )
                )
            ).scalar_one()
            return
        except NoResultFound:
            pass

        gia_type_obj = (
            await session.execute(select(GiaType).filter(GiaType.name == problem_data.gia_type))
        ).scalar_one_or_none()

        subject_obj = await session.execute(
            select(Subject).filter(Subject.hash == problem_data.subject_hash)
        )
        subject_obj = subject_obj.scalar_one_or_none()
        if subject_obj is None:
            subject_obj = Subject(name=problem_data.subject_name, hash=problem_data.subject_hash)
            session.add(subject_obj)

        problem = FipiBankProblem(
            problem_id=problem_data.problem_id,
            url=problem_data.url,
            condition_html=problem_data.condition_html,
            gia_types=[gia_type_obj] if gia_type_obj else [],
            subjects=[subject_obj],
            file_urls=[
                FipiBankProblemFile(file_url=file_url) for file_url in problem_data.file_urls
            ],
        )

        session.add(problem)
        await session.commit()


async def save_subject_problems(problems_data: list[ProblemData]) -> None:
    """All tasks must have the same gia_type and subject_hash"""
    async with async_session() as session, session.begin():
        problem_data = problems_data[0]
        gia_type_obj = (
            await session.execute(select(GiaType).filter(GiaType.name == problem_data.gia_type))
        ).scalar_one_or_none()

        subject_obj = await session.execute(
            select(Subject).filter(Subject.hash == problem_data.subject_hash)
        )
        subject_obj = subject_obj.scalar_one_or_none()
        if subject_obj is None:
            subject_obj = Subject(name=problem_data.subject_name, hash=problem_data.subject_hash)
            session.add(subject_obj)

        for problem_data in problems_data:
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
                    gia_types=[gia_type_obj] if gia_type_obj else [],
                    subjects=[subject_obj],
                    file_urls=[
                        FipiBankProblemFile(file_url=file_url)
                        for file_url in problem_data.file_urls
                    ],
                )
                session.add(problem)
        await session.commit()
