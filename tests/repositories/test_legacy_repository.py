import shutil
from pathlib import Path

from poetry.repositories.legacy_repository import LegacyRepository, Page

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse


class MockRepository(LegacyRepository):

    FIXTURES = Path(__file__).parent / "fixtures" / "legacy"

    def __init__(self) -> None:
        super().__init__("legacy", url="http://legacy.foo.bar", disable_cache=True)

    def _get_page(self, endpoint: str) -> Page | None:
        parts = endpoint.split("/")
        name = parts[1]

        fixture = self.FIXTURES / (name + ".html")
        if not fixture.exists():
            return

        with fixture.open(encoding="utf-8") as f:
            return Page(self._url + endpoint, f.read(), {})

    def _download(self, url: str, dest: Path) -> None:
        filename = urlparse.urlparse(url).path.rsplit("/")[-1]
        filepath = self.FIXTURES.parent / "pypi.org" / "dists" / filename

        shutil.copyfile(str(filepath), dest)
