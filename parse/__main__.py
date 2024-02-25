from __future__ import annotations

import asyncio
import json
import random
import time
from concurrent.futures import ProcessPoolExecutor
from types import TracebackType
from urllib.parse import urljoin

import aiohttp
import bs4
from bs4 import BeautifulSoup
from tqdm import tqdm

from config import CONVERT_SUBJECT_NAME_TO_ABBREVIATION
from database import register_models
from database.methods import save_multiple_problems
from database.models import FipiBankProblem


class FipiBankClient:
    def __init__(self, gia_type: str) -> None:
        if gia_type not in ["oge", "ege"]:
            raise ValueError(f'gia_type can be only "oge" or "ege", not {gia_type}')
        self.gia_type = gia_type

        self._BASE_URL = f"https://{gia_type}.fipi.ru/bank"
        self._BASE_INDEX_URL = f"{self._BASE_URL}/index.php"
        self._BASE_QUESTIONS_URL = f"{self._BASE_URL}/questions.php"
        self._PAGE_SIZE_LIMIT = 2**14

        connector = aiohttp.TCPConnector(ssl=False)  # to connect to fipi.ru
        self._session = aiohttp.ClientSession(connector=connector)

    async def __aenter__(self) -> FipiBankClient:
        return self

    async def _get(self, *args: int | str, **kwargs: [str, str]) -> str:
        async with self._session.get(*args, **kwargs, verify_ssl=False) as response:
            print(f"{response.status}: {response.url}")
            if response.status == 500:
                delay_between_retry = random.uniform(7.5, 15)  # noqa: S311
                print(f"Retrying {response.url}. Sleeping for {delay_between_retry} s.")
                await asyncio.sleep(delay_between_retry)
                return await self._get(*args, **kwargs)
            return await response.text()

    async def __aexit__(
        self, exc_type: type[BaseException], exc: BaseException, tb: TracebackType
    ) -> None:
        await self._session.close()

    async def get_subject_ids(self) -> dict[str, str]:
        main_page_html = await self._get(url=self._BASE_URL)
        soup = BeautifulSoup(main_page_html, "html.parser")
        exam_cards = soup.find_all("ul")[1].find_all("li")
        return {
            CONVERT_SUBJECT_NAME_TO_ABBREVIATION[i.get_text(strip=True)]: i.get("id")[2:]
            for i in exam_cards
        }

    @staticmethod
    def _get_problem_data_from_tag(
        problem_tag: bs4.Tag, subject: str, subject_id: str, gia_type: str
    ) -> FipiBankProblem:
        problem_id = problem_tag.get("id").lstrip("q")
        condition_html = str(problem_tag)
        base_url = f"https://{gia_type}.fipi.ru/bank"
        base_questions_url = f"{base_url}/questions.php"
        condition_image_urls = [
            urljoin(base_url, i.get("src").lstrip("../../"))
            for i in problem_tag.find_all("img", src=True)
        ]

        url = f"{base_questions_url}?search=1&proj={subject_id}&qid={problem_id}"
        return FipiBankProblem(
            problem_id=problem_id,
            subject=subject,
            url=url,
            gia_type=gia_type,
            condition_html=condition_html,
            condition_image_urls=";".join(condition_image_urls) or None,
        )

    async def _get_subject_problems_html(self, subject_id: str) -> str:
        params = {
            "proj": subject_id,
            "pagesize": self._PAGE_SIZE_LIMIT,
            "search": 1,
        }

        return await self._get(url=self._BASE_QUESTIONS_URL, params=params)

    @staticmethod
    def _parse_subject_problems_from_html(
        args: tuple[str, str, str, str],
    ) -> list[FipiBankProblem]:
        html, subject, subject_id, gia_type = args
        # print(subject, subject_id, gia_type)
        soup = BeautifulSoup(html, "html.parser")

        problem_cards = soup.find_all("div", class_="qblock")

        skip_next_card = False
        problems_data_list: list[FipiBankProblem] = []
        for first_card_tag, second_card_tag in zip(problem_cards, problem_cards[1:]):
            if skip_next_card:
                skip_next_card = False
                continue
            id_tag_text = first_card_tag.get("id")
            if id_tag_text is None:
                problem_tag = second_card_tag
                problem_tag.extend(first_card_tag.contents)
                skip_next_card = True
            else:
                problem_tag = first_card_tag
            problem_data = FipiBankClient._get_problem_data_from_tag(
                problem_tag, subject, subject_id, gia_type
            )
            problems_data_list.append(problem_data)
        return problems_data_list

    async def get_theme_names_and_ids(self, subject_id: str) -> dict[str, str]:
        params = {"proj": subject_id}
        html = await self._get(url=self._BASE_INDEX_URL, params=params)
        soup = BeautifulSoup(html, "html.parser")
        data = {}
        themes_block = soup.find("ul", class_="dropdown-menu")
        theme_tags = [
            i
            for i in themes_block.find_all("li", class_="dropdown-item")
            if "dropdown-header" not in i.get("class")
        ]
        for theme_tag in theme_tags:
            text = theme_tag.get_text(strip=True)
            id_str, title = text.split(" ", 1)
            data[id_str] = title

        return data

    async def parse_and_save_all_problems(self) -> None:
        t1 = time.perf_counter()
        subject_ids = await self.get_subject_ids()

        get_html_tasks = [
            asyncio.create_task(self._get_subject_problems_html(subject_id))
            for subject, subject_id in subject_ids.items()
        ]
        # The requests to the API of fipi.ru are heavy for their server,
        # so we can't make them asynchronously
        pages_htmls: list[str] = []
        for task in get_html_tasks:
            pages_htmls.append(await task)
            delay_between_chunks = random.uniform(15, 20)  # noqa: S311
            print(f"Sleeping for {delay_between_chunks} s between API requests.")
            await asyncio.sleep(delay_between_chunks)

        print("Got all htmls")

        with ProcessPoolExecutor(max_workers=4) as pool:
            data = [
                [html, subject, subject_id, self.gia_type]
                for html, (subject, subject_id) in zip(pages_htmls, subject_ids.items())
            ]
            results = pool.map(
                self._parse_subject_problems_from_html,
                data,
            )
            for i in tqdm(results):
                await save_multiple_problems(i)

        print(f"Total time: {time.perf_counter() - t1: .2f}")

    async def parse_subject_problems(self, subject: str, subject_id: str) -> None:
        params = {
            "proj": subject_id,
            "pagesize": self._PAGE_SIZE_LIMIT,
            "search": 1,
        }

        html = await self._get(url=self._BASE_QUESTIONS_URL, params=params)
        print(f"Started parsing {subject} {self.gia_type} problems.")
        t1 = time.perf_counter()
        soup = BeautifulSoup(html, "html.parser")
        print(
            f"Parsing {subject} {self.gia_type} problems"
            f"took {round(time.perf_counter() - t1, 1)}s."
        )
        problem_cards = soup.find_all("div", class_="qblock")
        print(f"Parsed {len(problem_cards)} qblock div tags.")

        skip_next_card = False
        problems_data_list: list[FipiBankProblem] = []
        for first_card_tag, second_card_tag in zip(problem_cards, problem_cards[1:]):
            if skip_next_card:
                skip_next_card = False
                continue
            id_tag_text = first_card_tag.get("id")
            if id_tag_text is None:
                problem_tag = second_card_tag
                problem_tag.extend(first_card_tag.contents)
                skip_next_card = True
            else:
                problem_tag = first_card_tag
            problem_data = self._get_problem_data_from_tag(
                problem_tag, subject, subject_id, self.gia_type
            )
            problems_data_list.append(problem_data)
        t1 = time.perf_counter()

        await save_multiple_problems(problems_data_list)
        print(
            f"Adding {subject} {self.gia_type} problems to database took "
            f"{round(time.perf_counter() - t1, 1)}s."
        )


async def main() -> None:
    await register_models()
    gia_type = "ege"
    async with FipiBankClient(gia_type) as client:
        subjects_ids = await client.get_subject_ids()
        themes_data = await client.get_theme_names_and_ids(subject_id=subjects_ids["inf"])
        print(json.dumps(themes_data, ensure_ascii=False, indent=4))
        await client.parse_and_save_all_problems()


if __name__ == "__main__":
    asyncio.run(main())
