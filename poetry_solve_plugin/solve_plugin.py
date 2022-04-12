from poetry.console.application import Application
from poetry.console.commands.lock import LockCommand
from poetry.plugins.application_plugin import ApplicationPlugin

from .installer import Installer
from .provider import Provider  # noqa: F401


class SolveCommand(LockCommand):

    name = "solve"
    description = "Solve and lock the project dependencies."

    help = """
The <info>solve</info> command reads the <comment>pyproject.toml</> file from the
current directory, processes it, and locks the dependencies in the\
 <comment>poetry.lock</>
file.

<info>poetry solve</info>
"""

    def handle(self) -> int:
        default_installer = self._installer
        self.set_installer(
            Installer(
                io=default_installer._io,
                env=default_installer._env,
                package=self.poetry.package,
                locker=self.poetry.locker,
                pool=self.poetry.pool,
                config=self.poetry.config,
                provider=Provider,
            )
        )

        return super().handle()


def factory():
    return SolveCommand()


class SolveApplicationPlugin(ApplicationPlugin):
    def activate(self, application: Application) -> None:
        print("aaaaa")
        application.command_loader.register_factory("solve", factory)
        print("bbbbbbb")
