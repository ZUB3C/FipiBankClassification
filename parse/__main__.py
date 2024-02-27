from __future__ import annotations

import asyncio
import json
import random
import re
import time
from types import TracebackType
from urllib.parse import urljoin

import aiohttp
from selectolax.parser import HTMLParser
from tqdm import tqdm

from config import SUBJECT_NAME_TO_ABBREVIATION
from database import FipiBankProblem, register_models, save_multiple_problems


class FipiBankClient:
    def __init__(self, gia_type: str) -> None:
        if gia_type not in ["oge", "ege"]:
            raise ValueError(f'gia_type can be only "oge" or "ege", not {gia_type}')
        self.gia_type = gia_type

        self._BASE_URL = f"https://{gia_type}.fipi.ru/bank"
        self._BASE_INDEX_URL = f"{self._BASE_URL}/index.php"
        self._BASE_QUESTIONS_URL = f"{self._BASE_URL}/questions.php"
        self._PAGE_SIZE_LIMIT = 2**12
        self._TIMEOUT = 60 * 5

        connector = aiohttp.TCPConnector(ssl=False)  # to connect to fipi.ru
        self._session = aiohttp.ClientSession(
            connector=connector,
        )

    async def __aenter__(self) -> FipiBankClient:
        return self

    async def _get(self, *args: int | str, **kwargs: [str, str]) -> str:
        async with self._session.get(
            *args, **kwargs, verify_ssl=False, timeout=self._TIMEOUT
        ) as response:
            # print(f"{response.status}: {response.url}")
            if response.status == 500:
                delay_between_retry = random.uniform(7.5, 15)  # noqa: S311
                # print(f"Retrying {response.url}. Sleeping for {delay_between_retry} s.")
                await asyncio.sleep(delay_between_retry)
                return await self._get(*args, **kwargs)
            return await response.text()

    async def __aexit__(
        self, exc_type: type[BaseException], exc: BaseException, tb: TracebackType
    ) -> None:
        await self._session.close()

    async def get_subject_ids(self) -> dict[str, str]:
        main_page_html = await self._get(url=self._BASE_URL)
        parser = HTMLParser(main_page_html)
        exam_cards = parser.css("ul")[1].css("li")
        return {
            SUBJECT_NAME_TO_ABBREVIATION[i.text(strip=True)]: i.attributes.get("id", "")[2:]
            for i in exam_cards
        }

    def _get_problem_data_from_tag(
        self, problem_tag: HTMLParser, subject: str, subject_id: str, gia_type: str
    ) -> FipiBankProblem:
        problem_id = problem_tag.css_first("div.qblock").attributes["id"].lstrip("q")
        condition_html = problem_tag.html

        condition_file_urls = []
        script_tags = problem_tag.css("script")
        image_url_pattern = re.compile(r"ShowPictureQ\w{0,3}\('(.+?)'\)")
        for script_tag in script_tags:
            script_content = script_tag.text()
            image_urls = re.findall(image_url_pattern, script_content)
            if image_urls:
                for image_url in image_urls:
                    image_url = urljoin(self._BASE_URL, image_url.lstrip("../../"))
                    condition_file_urls.append(image_url)

        url = f"{self._BASE_QUESTIONS_URL}?search=1&proj={subject_id}&qid={problem_id}"
        return FipiBankProblem(
            problem_id=problem_id,
            subject=subject,
            url=url,
            gia_type=gia_type,
            condition_html=condition_html,
            condition_file_urls=";".join(condition_file_urls) or None,
        )

    async def _get_subject_problems_html(self, subject_id: str) -> str:
        params = {
            "proj": subject_id,
            "pagesize": self._PAGE_SIZE_LIMIT,
            "search": 1,
        }

        return await self._get(url=self._BASE_QUESTIONS_URL, params=params)

    def _parse_subject_problems_from_html(
        self, html: str, subject: str, subject_id: str
    ) -> list[FipiBankProblem]:
        doc = HTMLParser(html)

        problem_cards = doc.css("div.qblock")

        skip_next_card = False
        problems_data_list: list[FipiBankProblem] = []
        for first_card_tag, second_card_tag in zip(problem_cards, problem_cards[1:]):
            if skip_next_card:
                skip_next_card = False
                continue
            id_tag_text = first_card_tag.attributes.get("id")
            if id_tag_text is None:
                problem_tag = second_card_tag
                second_card_tag.insert_before(first_card_tag)
                skip_next_card = True
            else:
                problem_tag = first_card_tag
            problem_data = self._get_problem_data_from_tag(
                problem_tag, subject, subject_id, self.gia_type
            )
            problems_data_list.append(problem_data)
        return problems_data_list

    async def get_theme_names_and_ids(self, subject_id: str) -> dict[str, str]:
        params = {"proj": subject_id}
        html = await self._get(url=self._BASE_INDEX_URL, params=params)
        parser = HTMLParser(html)
        data = {}
        themes_block = parser.css("ul.dropdown-menu")[0]
        theme_tags = [
            i
            for i in themes_block.css("li.dropdown-item")
            if "dropdown-header" not in i.attributes.get("class", "")
        ]
        for theme_tag in theme_tags:
            text = theme_tag.text(strip=True)
            id_str, title = text.split(" ", 1)
            data[id_str] = title
        return data

    async def parse_and_save_all_problems(self) -> None:
        t1 = time.perf_counter()
        subject_ids = await self.get_subject_ids()

        # The requests to the API of fipi.ru are heavy for their server,
        # so we can't make them asynchronously. Synchronous realization:
        pages_htmls: list[str] = []
        for subject, subject_id in tqdm(subject_ids.items(), desc="Synchronously fetching problems API"):
            pages_htmls.append(await self._get_subject_problems_html(subject_id))

        print("Got all htmls. Started parsing them")

        subject_problems_list: list[list[FipiBankProblem]] = []

        for html, (subject, subject_id) in zip(pages_htmls, subject_ids.items()):
            subject_problems_list.append(
                self._parse_subject_problems_from_html(html, subject, subject_id)
            )
        for subject_problems in tqdm(subject_problems_list, desc="Saving problems to database"):
            await save_multiple_problems(subject_problems)

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
        doc = HTMLParser(html)
        print(
            f"Parsing {subject} {self.gia_type} problems"
            f"took {round(time.perf_counter() - t1, 1)}s."
        )
        problem_cards = doc.css("div.qblock")
        print(f"Parsed {len(problem_cards)} qblock div tags.")

        skip_next_card = False
        problems_data_list: list[FipiBankProblem] = []
        for first_card_tag, second_card_tag in zip(problem_cards, problem_cards[1:]):
            if skip_next_card:
                skip_next_card = False
                continue
            id_tag_text = first_card_tag.attributes.get("id")
            if id_tag_text is None:
                problem_tag = second_card_tag
                second_card_tag.insert_before(first_card_tag)
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
        print(json.dumps(subjects_ids, ensure_ascii=False, indent=4))
        themes_data = await client.get_theme_names_and_ids(subject_id=subjects_ids["inf"])
        print(json.dumps(themes_data, ensure_ascii=False, indent=4))
        await client.parse_and_save_all_problems()


if __name__ == "__main__":
    asyncio.run(main())
