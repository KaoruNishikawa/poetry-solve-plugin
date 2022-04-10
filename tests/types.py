from __future__ import annotations

from typing import TYPE_CHECKING

from tests.compat import Protocol

if TYPE_CHECKING:
    from pathlib import Path

    from cleo.io.io import IO
    from cleo.testers.command_tester import CommandTester
    from poetry.config.config import Config
    from poetry.config.source import Source
    from poetry.installation import Installer
    from poetry.installation.executor import Executor
    from poetry.poetry import Poetry
    from poetry.utils.env import Env


class CommandTesterFactory(Protocol):
    def __call__(
        self,
        command: str,
        poetry: Poetry = None,
        installer: Installer = None,
        executor: Executor = None,
        environment: Env = None,
    ) -> CommandTester:
        ...


class SourcesFactory(Protocol):
    def __call__(self, poetry: Poetry, sources: Source, config: Config, io: IO) -> None:
        ...


class ProjectFactory(Protocol):
    def __call__(
        self,
        name: str = None,
        dependencies: dict[str, str] = None,
        dev_dependencies: dict[str, str] = None,
        pyproject_content: str = None,
        poetry_lock_content: str = None,
        install_deps: bool = True,
    ) -> Poetry:
        ...


class FixtureDirGetter(Protocol):
    def __call__(self, name: str) -> Path:
        ...
