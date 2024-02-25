from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


def chunks(iterable: Sequence[T], n: int) -> list[T]:
    return [iterable[i : i + n] for i in range(0, len(iterable), n)]
