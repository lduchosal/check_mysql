"""Fixtures for the end-to-end suite.

Unlike the unit and integration suites, these tests need the real MySQL
server configured in the repository's ``check_mysql.ini`` (see
``check_mysql init``). They are excluded from the default pytest run by
the ``e2e`` marker and gate ``pdm run publish`` and publish.sh through
``pdm run test-e2e``.
"""

import configparser
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INI_PATH = REPO_ROOT / "check_mysql.ini"
CLI_BINARY = Path(sys.executable).parent / "check_mysql"


@pytest.fixture(scope="session")
def ini_path():
    """Absolute path of the repository configuration; fail early when absent."""
    if not INI_PATH.exists():
        pytest.fail(
            f"{INI_PATH} not found — the e2e suite runs against the local "
            "MySQL server it configures (create it with: check_mysql init)"
        )
    return str(INI_PATH)


@pytest.fixture(scope="session")
def mysql_settings(ini_path):
    """The [mysql] section of the repository configuration."""
    config = configparser.ConfigParser()
    config.read(ini_path)
    return config["mysql"]


@pytest.fixture
def run_cli(tmp_path):
    """Run the installed check_mysql binary from a neutral working directory.

    The console script is the artifact Nagios executes in production; the
    neutral cwd keeps the repo-root check_mysql.ini out of the default
    config lookup, so every test states its configuration explicitly.
    """

    def _run(*args, stdin=None):
        return subprocess.run(
            [str(CLI_BINARY), *args],
            cwd=tmp_path,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    return _run
