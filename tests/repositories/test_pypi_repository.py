import json
import shutil
from pathlib import Path

from poetry.repositories.pypi_repository import PyPiRepository


class MockRepository(PyPiRepository):

    JSON_FIXTURES = Path(__file__).parent / "fixtures" / "pypi.org" / "json"
    DIST_FIXTURES = Path(__file__).parent / "fixtures" / "pypi.org" / "dists"

    def __init__(self, fallback: bool = False):
        super().__init__(url="http://foo.bar", disable_cache=True, fallback=fallback)

    def _get(self, url: str) -> dict | None:
        parts = url.split("/")[1:]
        name = parts[0]
        if len(parts) == 3:
            version = parts[1]
        else:
            version = None

        if not version:
            fixture = self.JSON_FIXTURES / (name + ".json")
        else:
            fixture = self.JSON_FIXTURES / name / (version + ".json")
            if not fixture.exists():
                fixture = self.JSON_FIXTURES / (name + ".json")

        if not fixture.exists():
            return

        with fixture.open(encoding="utf-8") as f:
            return json.loads(f.read())

    def _download(self, url: str, dest: Path) -> None:
        filename = url.split("/")[-1]

        fixture = self.DIST_FIXTURES / filename

        shutil.copyfile(str(fixture), dest)
