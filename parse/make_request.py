import requests
from fake_useragent import FakeUserAgent

from exceptions import TooManyRetries


def get_page_html(session: requests.sessions.Session, url: str, *, params: dict = None,
                  retries_count: int = 0, max_retries: int = 10) -> str:
    if params is None:
        params = {}

    with session.get(url, params=params, headers={'user-agent': FakeUserAgent().random}, verify=False) as response:
        print(f'Fetched {response.url}')
        response.raise_for_status()
        return response.text
        # if response.status_code == 200:
        #     return response.text
        # elif response.status_code != 404:
        #     print(f'Response status {response.status_code} from {response.url}. Retrying ({retries_count + 1}).')
        #     if retries_count == max_retries:
        #         raise TooManyRetries(f'Too many retries was made to {response.url} with params = {params}')
        #     return get_page_html(session, url, retries_count=retries_count + 1, max_retries=max_retries, params=params)
