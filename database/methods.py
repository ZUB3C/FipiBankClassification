from collections.abc import Coroutine
from typing import Any

from sqlalchemy import CursorResult, insert, select

from database.models import FipiBankProblem, async_session


async def save_problem(
    problem_data: FipiBankProblem,
) -> Coroutine[Any, Any, CursorResult[Any]] | None:
    async with async_session() as session:
        query = select(FipiBankProblem).where(
            problem_data.problem_id == FipiBankProblem.problem_id
        )
        exists = await session.execute(query)
        if not exists.scalar():
            session.execute(insert(problem_data))
    return None


async def save_multiple_problems(problems_data_list: list[FipiBankProblem]) -> None:
    async with async_session() as session:
        new_problems = []
        for problem in problems_data_list:
            query = select(FipiBankProblem).where(problem.problem_id == FipiBankProblem.problem_id)
            exists = await session.execute(query)
            if not exists.scalar():
                new_problems.append(problem)
        session.add_all(new_problems)
        await session.commit()
