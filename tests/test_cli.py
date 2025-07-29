from typer.testing import CliRunner

from openaleph_procrastinate import __version__
from openaleph_procrastinate.cli import cli

runner = CliRunner()


def test_cli():

    res = runner.invoke(cli, "--version")
    assert res.exit_code == 0
    assert res.stdout.strip() == __version__
