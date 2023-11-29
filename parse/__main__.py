import json
import time
from datetime import timedelta, datetime
from typing import Literal, TypeVar
from urllib.parse import urljoin

import bs4
import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from config import CONVERT_SUBJECT_NAME_TO_ABBREVIATION
from database import register_models
from database.methods.insert import save_problem
from parse.make_request import get_page_html

GiaType = TypeVar('GiaType', Literal["oge"], Literal["ege"])


def get_subject_ids(session: requests.sessions.Session, gia_type: GiaType) -> dict[str: str]:
    url = f'https://{gia_type}.fipi.ru/bank/'
    main_page_html = get_page_html(session, url)
    soup = BeautifulSoup(main_page_html, 'html.parser')
    exam_cards = soup.find_all('ul')[1].find_all('li')
    subjects_data = {
        CONVERT_SUBJECT_NAME_TO_ABBREVIATION.get(i.get_text(strip=True)): i.get('id')[2:] for i in exam_cards
    }
    # print(json.dumps(subjects_data, indent='\t', ensure_ascii=False))
    return subjects_data


def parse_subject_problems(session: requests.sessions.Session, subject: str, subject_id: str,
                           gia_type: GiaType) -> None:
    params = dict(
        proj=subject_id,
        pagesize=2 ** 12,
        search=1,
    )
    params |= {
        'theme': '',
        'qlevel': '',
        'qkind': '',
        'qid': '',
        'zid': '',
        'solved': '',
        'favorite': '',
    }

    html = get_page_html(session, f'https://{gia_type}.fipi.ru/bank/questions.php', params=params)
    print(f'Starting parsing {subject} {gia_type} problems.')
    t1 = time.perf_counter()
    soup = BeautifulSoup(html, 'html.parser')
    print(f'Parsing {subject} {gia_type} problems took {round(time.perf_counter() - t1, 1)}s.')
    problem_cards = soup.find_all('div', class_='qblock')
    print(f"Parsed {len(problem_cards)} qblock div tags.")

    t1 = time.perf_counter()
    skip_next_card = False
    for first_card_tag, second_card_tag in zip(problem_cards, problem_cards[1:]):
        if skip_next_card:
            skip_next_card = False
            continue
        id_tag_text = first_card_tag.get('id')
        if id_tag_text is None:
            problem_tag = second_card_tag
            problem_tag.extend(first_card_tag.contents)
            skip_next_card = True
            # problem_id = problem_tag.get('id')[1:]
            # print(problem_id)
        else:
            problem_tag = first_card_tag
        problem_data = get_problem_data_from_tag(problem_tag, subject, subject_id, gia_type)
        save_problem(problem_data)
    print(f'Adding {subject} {gia_type} problems to database took {round(time.perf_counter() - t1, 1)}s.')


def get_problem_data_from_tag(problem_tag: bs4.Tag, subject: str, subject_id: str, gia_type: GiaType) -> dict:
    base_url = f'https://{gia_type}.fipi.ru/'
    problem_id = problem_tag.get('id')[1:]
    problem_data = dict(
        problem_id=problem_id,
        subject=subject,
        condition_html=str(problem_tag),
        raw_condition_text=problem_tag.get_text(strip=True),
        condition_images=';'.join(
            [urljoin(base_url, i.get('src')[5:])
             for i in problem_tag.find_all('img', src=True)]
        ),
        url=urljoin(base_url, f'/bank/questions.php?search=1&proj={subject_id}&qid={problem_id}'),
        gia_type=gia_type,
        new_bank=True
    )
    return problem_data


def main():
    # Remove unverified HTTPS request warning
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    register_models()

    for gia_type in ['ege', 'oge']:
        with requests.session() as session:
            subjects_data = get_subject_ids(session, gia_type)
            for subject, subject_id in tuple(subjects_data.items()):
                parse_subject_problems(session, subject, subject_id, gia_type)


if __name__ == '__main__':
    start_timestamp = time.perf_counter()
    main()
    seconds_delta = time.perf_counter() - start_timestamp
    delta_time = timedelta(seconds=seconds_delta)
    print(f'Scrapping all problems took {(datetime.min + delta_time).strftime("%H:%M:%S")}')
