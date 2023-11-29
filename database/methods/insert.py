from sqlalchemy.exc import NoResultFound

from database import Database
from database.models import FIPIBankProblems


def save_problem(problem_data: dict) -> None:
    # print(f'Saving problem with id = {problem_data["problem_id"]}')
    # print(problem_data)
    session = Database().session
    add_problem_to_db = False
    try:
        problem_in_db = session.query(FIPIBankProblems.problem_id, FIPIBankProblems.subject) \
            .filter(FIPIBankProblems.problem_id == problem_data['problem_id'] and
                    FIPIBankProblems.subject == problem_data['subject']).one()
        # print('\n', problem_in_db, '\n')
        if not problem_in_db:
            add_problem_to_db = True
    except NoResultFound:
        # if not (problem_data['problem_id'], problem_data['subject']) in problem_in_db:
        add_problem_to_db = True
    if add_problem_to_db:
        session.add(FIPIBankProblems(**problem_data))
        session.commit()


async def save_problem_async(problem_data: dict) -> None:
    session = Database().session
    try:
        session.query(FIPIBankProblems.problem_id) \
            .filter(
            FIPIBankProblems.subject == problem_data['subject'] and
            FIPIBankProblems.problem_id == problem_data['problem_id']
        ).one()
        print(f'Problem with id = {problem_data["problem_id"]} already in database.')
    except NoResultFound:
        print(f'Saving problem with id = {problem_data["problem_id"]}.')
        session.add(FIPIBankProblems(**problem_data))
    session.commit()
