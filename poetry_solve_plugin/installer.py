from __future__ import annotations

from typing import TYPE_CHECKING

from cleo.io.null_io import NullIO

from poetry.installation.executor import Executor
from poetry.installation.installer import Installer as BaseInstaller
from poetry.repositories import Pool
from poetry.repositories import Repository

from .provider import Provider


if TYPE_CHECKING:
    from cleo.io.io import IO
    from poetry.core.packages.project_package import ProjectPackage

    from poetry.config.config import Config
    from poetry.packages import Locker
    from poetry.utils.env import Env


class Installer(BaseInstaller):
    def __init__(
        self,
        io: IO,
        env: Env,
        package: ProjectPackage,
        locker: Locker,
        pool: Pool,
        config: Config,
        installed: Repository | None = None,
        executor: Executor | None = None,
        provider: Provider | None = Provider,
    ):
        super().__init__(io, env, package, locker, pool, config, installed, executor)

        self._provider = provider

    @property
    def provider(self) -> Provider:
        return self._provider

    def _do_refresh(self) -> int:
        from poetry.puzzle.solver import Solver

        # Checking extras
        for extra in self._extras:
            if extra not in self._package.extras:
                raise ValueError(f"Extra [{extra}] is not specified.")

        locked_repository = self._locker.locked_repository(True)
        solver = Solver(
            self._package,
            self._pool,
            locked_repository,
            locked_repository,
            self._io,
            self._provider(self._package, self._pool, self._io),
        )

        ops = solver.solve(use_latest=[]).calculate_operations()

        local_repo = Repository()
        self._populate_local_repo(local_repo, ops)

        self._write_lock_file(local_repo, force=True)

        return 0

    def _do_install(self, local_repo: Repository) -> int:
        from poetry.puzzle.solver import Solver

        locked_repository = Repository()
        if self._update:
            if self._locker.is_locked() and not self._lock:
                locked_repository = self._locker.locked_repository(True)

                # If no packages have been whitelisted (The ones we want to update),
                # we whitelist every package in the lock file.
                if not self._whitelist:
                    for pkg in locked_repository.packages:
                        self._whitelist.append(pkg.name)

            # Checking extras
            for extra in self._extras:
                if extra not in self._package.extras:
                    raise ValueError(f"Extra [{extra}] is not specified.")

            self._io.write_line("<info>Updating dependencies</>")
            solver = Solver(
                self._package,
                self._pool,
                self._installed_repository,
                locked_repository,
                self._io,
                self._provider(self._package, self._pool, self._io),
            )

            ops = solver.solve(use_latest=self._whitelist).calculate_operations()
        else:
            self._io.write_line("<info>Installing dependencies from lock file</>")

            locked_repository = self._locker.locked_repository(True)

            if not self._locker.is_fresh():
                self._io.write_error_line(
                    "<warning>"
                    "Warning: poetry.lock is not consistent with pyproject.toml. "
                    "You may be getting improper dependencies. "
                    "Run `poetry lock [--no-update]` to fix it."
                    "</warning>"
                )

            for extra in self._extras:
                if extra not in self._locker.lock_data.get("extras", {}):
                    raise ValueError(f"Extra [{extra}] is not specified.")

            # If we are installing from lock
            # Filter the operations by comparing it with what is
            # currently installed
            ops = self._get_operations_from_lock(locked_repository)

        self._populate_local_repo(local_repo, ops)

        if self._update:
            self._write_lock_file(local_repo)

            if self._lock:
                # If we are only in lock mode, no need to go any further
                return 0

        if self._groups is not None:
            root = self._package.with_dependency_groups(list(self._groups), only=True)
        else:
            root = self._package.without_optional_dependency_groups()

        if self._io.is_verbose():
            self._io.write_line("")
            self._io.write_line(
                "<info>Finding the necessary packages for the current system</>"
            )

        # We resolve again by only using the lock file
        pool = Pool(ignore_repository_names=True)

        # Making a new repo containing the packages
        # newly resolved and the ones from the current lock file
        repo = Repository()
        for package in local_repo.packages + locked_repository.packages:
            if not repo.has_package(package):
                repo.add_package(package)

        pool.add_repository(repo)

        solver = Solver(
            root,
            pool,
            self._installed_repository,
            locked_repository,
            NullIO(),
            self._provider(self._package, self._pool, self._io),
        )
        # Everything is resolved at this point, so we no longer need
        # to load deferred dependencies (i.e. VCS, URL and path dependencies)
        solver.provider.load_deferred(False)

        with solver.use_environment(self._env):
            ops = solver.solve(use_latest=self._whitelist).calculate_operations(
                with_uninstalls=self._requires_synchronization,
                synchronize=self._requires_synchronization,
            )

        if not self._requires_synchronization:
            # If no packages synchronisation has been requested we need
            # to calculate the uninstall operations
            from poetry.puzzle.transaction import Transaction

            transaction = Transaction(
                locked_repository.packages,
                [(package, 0) for package in local_repo.packages],
                installed_packages=self._installed_repository.packages,
                root_package=root,
            )

            ops = [
                op
                for op in transaction.calculate_operations(with_uninstalls=True)
                if op.job_type == "uninstall"
            ] + ops

        # We need to filter operations so that packages
        # not compatible with the current system,
        # or optional and not requested, are dropped
        self._filter_operations(ops, local_repo)

        # Execute operations
        return self._execute(ops)
