from poetry.console.application import Application
from poetry.console.commands.lock import LockCommand
from poetry.plugins.application_plugin import ApplicationPlugin


class Solve(LockCommand):

    name = "solve"
    description = "Solve and lock the project dependencies."

    help = """
The <info>solve</info> command reads the <comment>pyproject.toml</> file from the
current directory, processes it, and locks the dependencies in the\
 <comment>poetry.lock</>
file.

<info>poetry solve</info>
"""

    def handle(self):
        ...  # won't use self.installer, but re-implement it for locking only.


def factory():
    return Solve()


class SolveApplicationPlugin(ApplicationPlugin):
    def activate(self, application: Application) -> None:
        application.command_loader.register_factory("solve", factory)
