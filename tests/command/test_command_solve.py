from __future__ import annotations

from typing import TYPE_CHECKING
# from unittest.mock import Mock

import pytest

from poetry.core.packages.package import Package

from tests.markers import MARKER_PY


if TYPE_CHECKING:
    # from _pytest.monkeypatch import MonkeyPatch
    from cleo.testers.command_tester import CommandTester
    from poetry.poetry import Poetry
    from poetry.repositories import Repository

    from tests.types import CommandTesterFactory
    from tests.types import ProjectFactory


PYPROJECT_CONTENT = """\
[tool.poetry]
name = "simple-project"
version = "1.2.3"
description = "Some description."
authors = [
    "Kaoru Nishikawa <k.nishikawa@a.phys.nagoya-u.ac.jp>"
]
license = "MIT"

readme = "README.md"

homepage = "https://github.com/KaoruNishikawa/poetry-solve-plugin"
repository = "https://github.com/KaoruNishikawa/poetry-solve-plugin"
documentation = "https://github.com/KaoruNishikawa/poetry-solve-plugin/tree/main/docs"

keywords = ["packaging", "dependency", "poetry"]

classifiers = [
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Libraries :: Python Modules"
]

# Requirements
[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
foo = "^1.0"
bar = { version = "^1.1", optional = true }

[tool.poetry.extras]
feature_bar = ["bar"]
"""


@pytest.fixture(autouse=True)
def setup(repo: Repository) -> None:
    repo.add_package(Package("foo", "1.0.0"))
    repo.add_package(Package("bar", "1.1.0"))


@pytest.fixture
def poetry(project_factory: ProjectFactory):
    return project_factory(name="solve", pyproject_content=PYPROJECT_CONTENT)


@pytest.fixture
def tester(
    command_tester_factory: CommandTesterFactory, poetry: Poetry
) -> CommandTester:
    return command_tester_factory("solve", poetry=poetry)


# def _export_requirements(tester: CommandTester, poetry: Poetry) -> None:
#     tester.execute("--format requirements.txt --output requirements.txt")

#     requirements = poetry.file.parent / "requirements.txt"
#     assert requirements.exists()

#     with requirements.open(encoding="utf-8") as f:
#         content = f.read()

#     assert poetry.locker.lock.exists()

#     expected = f"""\
# foo==1.0.0 ; {MARKER_PY}
# """

#     assert expected == content


# def test_export_exports_requirements_txt_file_locks_if_no_lock_file(
#     tester: CommandTester, poetry: Poetry
# ):
#     assert not poetry.locker.lock.exists()
#     _export_requirements(tester, poetry)
#     assert "The lock file does not exist. Locking." in tester.io.fetch_error()


# def test_export_exports_requirements_txt_uses_lock_file(
#     tester: CommandTester, poetry: Poetry, do_lock: None
# ):
#     _export_requirements(tester, poetry)
#     assert "The lock file does not exist. Locking." not in tester.io.fetch_error()


# def test_export_fails_on_invalid_format(tester: CommandTester, do_lock: None):
#     with pytest.raises(ValueError):
#         tester.execute("--format invalid")


# def test_export_prints_to_stdout_by_default(tester: CommandTester, do_lock: None):
#     tester.execute("--format requirements.txt")
#     expected = f"""\
# foo==1.0.0 ; {MARKER_PY}
# """
#     assert expected == tester.io.fetch_output()


# def test_export_uses_requirements_txt_format_by_default(
#     tester: CommandTester, do_lock: None
# ):
#     tester.execute()
#     expected = f"""\
# foo==1.0.0 ; {MARKER_PY}
# """
#     assert expected == tester.io.fetch_output()


# def test_export_includes_extras_by_flag(tester: CommandTester, do_lock: None):
#     tester.execute("--format requirements.txt --extras feature_bar")
#     expected = f"""\
# bar==1.1.0 ; {MARKER_PY}
# foo==1.0.0 ; {MARKER_PY}
# """
#     assert expected == tester.io.fetch_output()
