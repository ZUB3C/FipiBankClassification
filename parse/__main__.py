from __future__ import annotations

import asyncio
import itertools
import random
import re
import time
import typing
from typing import Any
from urllib.parse import urlencode, urljoin

import aiohttp
from selectolax.parser import HTMLParser, Node
from tqdm import tqdm

from database import register_models, save_subject_problems
from parse.problem_data import ProblemData, ThemeData

if typing.TYPE_CHECKING:
    from types import TracebackType


class FipiBankClient:
    _FIPIBANK_API_PAGE_SIZE_LIMIT = 2**12
    _TIMEOUT = 60
    _base_url: str = ""
    _base_index_url: str = ""
    _base_questions_url: str = ""

    def __init__(self, gia_type: str) -> None:
        self.set_gia_type(gia_type)
        self._gia_type = gia_type

        self._session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False),  # disable ssl to connect to fipi.ru,
            timeout=aiohttp.ClientTimeout(self._TIMEOUT),
        )

    def set_gia_type(self, gia_type: str) -> None:
        if gia_type not in ["oge", "ege"]:
            raise ValueError(f'gia_type can be only "oge" or "ege", not {gia_type}')
        self._base_url = f"https://{gia_type}.fipi.ru/bank"
        self._base_index_url = f"{self._base_url}/index.php"
        self._base_questions_url = f"{self._base_url}/questions.php"

    async def get_subject_ids(self) -> dict[str, str]:
        main_page_html = await self._get(url=self._base_url)
        parser = HTMLParser(main_page_html)
        exam_cards = parser.css("ul")[1].css("li")
        return {i.text(strip=True): i.attributes.get("id", "")[2:] for i in exam_cards}

    async def get_theme_names_and_ids(self, subject_hash: str) -> dict[str, str]:
        params = {"proj": subject_hash}
        html = await self._get(url=self._base_index_url, params=params)
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
            id_str, title = text.split(sep=" ", maxsplit=1)
            data[id_str] = title
        return data

    async def parse_and_save_all_problems(self, subject_names: list[str] | None = None) -> None:
        t1 = time.perf_counter()
        subject_ids = await self.get_subject_ids()
        if subject_names:
            subject_ids = {
                subject_name: subject_hash
                for subject_name, subject_hash in subject_ids.items()
                if subject_name in subject_names
            }
            print(f"Subjects to parse problems: {list(subject_ids.keys())}")
        get_pages_htmls_tasks: list[asyncio.Task[str]] = []
        subject_themes_data: dict[
            str, dict[str, str]
        ] = {}  # key -- hash, value -- themes_data dict
        for subject_name, subject_hash in subject_ids.items():
            themes_data = await self.get_theme_names_and_ids(subject_hash=subject_hash)
            subject_themes_data[subject_hash] = themes_data
            for theme_codifier_id, theme_name in themes_data.items():
                get_pages_htmls_tasks.append(
                    asyncio.create_task(
                        self._get_subject_problems_html(
                            subject_hash=subject_hash, theme_ids=[theme_codifier_id]
                        )
                    )
                )

        pages_htmls: tuple[str] = await asyncio.gather(*get_pages_htmls_tasks)

        print("Got all htmls. Started parsing them")

        all_problems = []

        for subject_name, subject_hash in tqdm(
            subject_ids.items(), desc="Parsing subjects problems"
        ):
            themes_data = subject_themes_data[subject_hash]
            subject_problems_list: list[ProblemData] = []  # Store problems for current subject
            for html, (theme_codifier_id, theme_name) in zip(
                pages_htmls, themes_data.items(), strict=False
            ):
                subject_problems: list[ProblemData] = self._parse_subject_problems_from_html(
                    html, subject_name, subject_hash
                )
                for subject_problem in subject_problems:
                    subject_problem.themes = [
                        ThemeData(codifier_id=theme_codifier_id, name=theme_name)
                    ]
                subject_problems_list.extend(subject_problems)

            # Process and set themes for each problem in the subject
            for problem_data in subject_problems_list:
                all_problem_themes = self._get_all_problem_themes_data(
                    problem_data, subject_problems_list
                )
                problem_data.themes = all_problem_themes
                all_problems.append(problem_data)
        await save_subject_problems(all_problems)
        print(f"Total time: {time.perf_counter() - t1: .2f}")

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> str:
        if not params:
            params = {}
        try:
            async with self._session.get(
                url=url, params=params, timeout=self._TIMEOUT
            ) as response:
                print(f"GET {response.status}: {response.url}")
                if response.status == 500:
                    delay_between_retry = random.uniform(7.5, 15)
                    print(f"Retrying {response.url}. Sleeping for {delay_between_retry} s.")
                    await asyncio.sleep(delay_between_retry)
                    return await self._get(url=url, params=params)
                return await response.text()
        except (TimeoutError, aiohttp.ServerDisconnectedError):
            delay_between_retry = random.uniform(7.5, 15)
            print(
                f"Retrying {urljoin(url, '?' + urlencode(params))}."
                f"Sleeping for {delay_between_retry} s."
            )
            await asyncio.sleep(delay_between_retry)
            return await self._get(url=url, params=params)

    def _get_problem_data_from_tag(
        self, problem_tag: HTMLParser | Node, subject_name: str, subject_hash: str, gia_type: str
    ) -> ProblemData:
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
                    image_url = urljoin(self._base_url, image_url.removeprefix("../../"))
                    condition_file_urls.append(image_url)

        url = f"{self._base_questions_url}?search=1&proj={subject_hash}&qid={problem_id}"
        return ProblemData(
            problem_id=problem_id,
            subject_name=subject_name,
            subject_hash=subject_hash,
            url=url,
            gia_type=gia_type,
            condition_html=condition_html,
            file_urls=condition_file_urls,
            themes=[],
        )

    async def _get_subject_problems_html(
        self, subject_hash: str, *, theme_ids: list[str] | None = None
    ) -> str:
        params = {
            "search": 1,
            "pagesize": self._FIPIBANK_API_PAGE_SIZE_LIMIT,
            "proj": subject_hash,
            "theme": ",".join(theme_ids) if theme_ids else "",
        }

        return await self._get(url=self._base_questions_url, params=params)

    def _parse_subject_problems_from_html(
        self, html: str, subject_name: str, subject_hash: str
    ) -> list[ProblemData]:
        doc = HTMLParser(html)

        problem_cards = doc.css("div.qblock")

        skip_next_card = False
        problems_data_list: list[ProblemData] = []
        for first_card_tag, second_card_tag in itertools.pairwise(problem_cards):
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
                problem_tag, subject_name, subject_hash, self._gia_type
            )
            problems_data_list.append(problem_data)
        return problems_data_list

    @staticmethod
    def _get_all_problem_themes_data(
        problem_data: ProblemData, subject_problems: list[ProblemData]
    ) -> list[ThemeData]:
        all_problem_themes = []
        for prob in subject_problems:
            if prob.problem_id == problem_data.problem_id:
                all_problem_themes.extend(prob.themes)
        return all_problem_themes

    async def __aenter__(self) -> FipiBankClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._session.close()


async def main() -> None:
    await register_models()

    async with FipiBankClient("ege") as client:
        await client.parse_and_save_all_problems(subject_names=["Информатика и ИКТ"])


if __name__ == "__main__":
    asyncio.run(main())
