from abc import ABC
from pathlib import Path
from typing import Final


class PathControl(ABC):
    ROOT: Final = Path(__file__).parent.parent

    @classmethod
    def get(cls, path: str) -> Path:
        return cls.ROOT.joinpath(path)
