from __future__ import annotations

from app.schemas import PaperRecord
from app.sources.base import BaseSource


class CVFSource(BaseSource):
    name = "cvf"

    def __init__(self, *, base_url: str = "https://openaccess.thecvf.com") -> None:
        super().__init__(base_url=base_url)

    def fetch(self) -> list[PaperRecord]:
        raise NotImplementedError("CVF source is not implemented for this MVP")
