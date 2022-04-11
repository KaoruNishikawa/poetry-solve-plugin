from __future__ import annotations

from typing import Any, TYPE_CHECKING

import pytest
from cleo.io.null_io import NullIO
from poetry.core.packages.project_package import ProjectPackage
from poetry.core.packages.vcs_dependency import VCSDependency

from poetry.factory import Factory
from poetry.puzzle.solver import Solver
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.pool import Pool
from poetry.repositories.repository import Repository
from tests.helpers import get_dependency, get_package

from poetry_solve_plugin.provider import Provider as BaseProvider

if TYPE_CHECKING:
    from poetry.installation.operations import OperationTypes
    from poetry.puzzle.transaction import Transaction

DEFAULT_SOURCE_REF = (
    VCSDependency("poetry", "git", "git@github.com:python-poetry/poetry.git").branch
    or "HEAD"
)


class Provider(BaseProvider):
    def set_package_python_versions(self, python_versions: str) -> None:
        self._package.python_versions = python_versions
        self._python_constraint = self._package.python_constraint


@pytest.fixture
def io() -> NullIO:
    return NullIO()


@pytest.fixture
def package() -> ProjectPackage:
    return ProjectPackage("root", "1.0")


@pytest.fixture
def installed() -> InstalledRepository:
    return InstalledRepository()


@pytest.fixture
def locked() -> Repository:
    return Repository()


@pytest.fixture
def repo() -> Repository:
    return Repository()


@pytest.fixture
def pool(repo: Repository) -> Repository:
    return Pool([repo])


@pytest.fixture
def solver(
    package: ProjectPackage,
    pool: Pool,
    installed: InstalledRepository,
    locked: Repository,
    io: NullIO,
) -> Solver:
    return Solver(
        package, pool, installed, locked, io, provider=Provider(package, pool, io)
    )


def check_solver_result(
    transaction: Transaction, expected: list[dict[str, Any]], synchronize: bool = False
) -> list[OperationTypes]:
    for e in expected:
        if "skipped" not in e:
            e["skipped"] = False

    result = []
    ops = transaction.calculate_operations(synchronize=synchronize)
    for op in ops:
        if op.job_type == "update":
            result.append(
                {
                    "job": "update",
                    "from": op.initial_package,
                    "to": op.target_package,
                    "skipped": op.skipped,
                }
            )
        else:
            job = "remove" if op.job_type == "uninstall" else "install"
            result.append({"job": job, "package": op.package, "skipped": op.skipped})

    assert result == expected
    return ops


def test_solver_install_single(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    repo.add_package(package_a)

    transaction = solver.solve([get_dependency("A")])

    check_solver_result(transaction, [{"job": "install", "package": package_a}])


def test_solver_duplicate_dependencies_both_in_project_and_sub_dependency(
    solver: Solver, repo: Repository, package: ProjectPackage
):
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(
        Factory.create_dependency("B", {"version": "^3.0", "python": "<3.8"})
    )
    package.add_dependency(
        Factory.create_dependency("B", {"version": "^5.0", "python": ">=3.8"})
    )

    package_a = get_package("A", "1.0")
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^3.0", "python": "<3.8"})
    )
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^5.0", "python": ">=3.8"})
    )
    package_a.add_dependency(Factory.create_dependency("B", ">=3.0, <6.0"))

    package_b30 = get_package("B", "3.0")
    package_b50 = get_package("B", "5.0")

    repo.add_package(package_a)
    repo.add_package(package_b30)
    repo.add_package(package_b50)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b30},
            {"job": "install", "package": package_b50},
            {"job": "install", "package": package_a},
        ],
    )
