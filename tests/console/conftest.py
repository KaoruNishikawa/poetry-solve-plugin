from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from poetry.factory import Factory
from poetry.repositories import Pool
from poetry.utils.env import MockEnv
from tests.helpers import PoetryTestApplication, TestLocker

if TYPE_CHECKING:
    from poetry.poetry import Poetry
    from tests.conftest import Config
    from tests.helpers import TestRepository


@pytest.fixture
def env(tmp_dir: str) -> MockEnv:
    path = Path(tmp_dir) / ".venv"
    path.mkdir(parents=True)
    return MockEnv(path=path, is_venv=True)


@pytest.fixture
def project_directory() -> str:
    return "simple_project"


@pytest.fixture
def poetry(repo: TestRepository, project_directory: str, config: Config) -> Poetry:
    p = Factory().create_poetry(
        Path(__file__).parent.parent / "fixtures" / project_directory
    )
    p.set_locker(TestLocker(p.locker.lock.path, p.locker._local_config))

    with p.file.path.open(encoding="utf-8") as f:
        content = f.read()

    p.set_config(config)

    pool = Pool()
    pool.add_repository(repo)
    p.set_pool(pool)

    yield p

    with p.file.path.open("w", encoding="utf-8") as f:
        f.write(content)


@pytest.fixture
def app(poetry: Poetry) -> PoetryTestApplication:
    app_ = PoetryTestApplication(poetry)

    return app_
