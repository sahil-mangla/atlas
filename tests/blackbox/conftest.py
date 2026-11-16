"""Run the real ``atlas`` CLI in a subprocess with the network cut off.

Each invocation is a fresh interpreter in an empty working directory with a
minimal environment, which is how a first-time user meets the tool. A
``sitecustomize`` module injected through ``PYTHONPATH`` makes every outbound
socket connection fail *and* records the attempt in a log file, so a network
call is detected even when the application swallows the resulting exception.
"""

import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_NETWORK_GUARD = """
import os
import socket

_LOG = os.environ["ATLAS_TEST_NETWORK_LOG"]


def _blocked(*args, **_kwargs):
    with open(_LOG, "a", encoding="utf-8") as handle:
        handle.write(repr(args[-1:]) + "\\n")
    raise OSError("network access is blocked in black-box tests")


socket.socket.connect = _blocked
socket.socket.connect_ex = _blocked
socket.create_connection = _blocked
socket.getaddrinfo = _blocked
"""

_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_SYSTEM_ENV = ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")


@dataclass(frozen=True)
class CliResult:
    """Outcome of one ``atlas`` invocation."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return self.stdout + self.stderr

    def first_uuid(self) -> str:
        match = _UUID.search(self.stdout)
        assert match, f"no UUID in output:\n{self.output}"
        return match.group()


@dataclass(frozen=True)
class Cli:
    """A sandboxed ``atlas`` command bound to one working directory."""

    cwd: Path
    network_log: Path
    _guard_dir: Path

    def __call__(
        self, *args: str, env: Mapping[str, str | None] | None = None
    ) -> CliResult:
        """Run ``atlas *args``; an ``env`` value of ``None`` unsets that variable."""
        environment = {key: os.environ[key] for key in _SYSTEM_ENV if key in os.environ}
        environment.update(
            {
                "HOME": str(self.cwd),
                "USERPROFILE": str(self.cwd),
                "PYTHONPATH": os.pathsep.join([str(self._guard_dir), str(REPO_ROOT)]),
                "PYTHONIOENCODING": "utf-8",
                "ATLAS_TEST_NETWORK_LOG": str(self.network_log),
                "ATLAS_AI_PROTOCOL": "SCRIPTED",
            }
        )
        for name, value in (env or {}).items():
            if value is None:
                environment.pop(name, None)
            else:
                environment[name] = value
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                "from atlas_eng.clients.cli.application import main; main()",
                *args,
            ],
            cwd=self.cwd,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
        return CliResult(completed.returncode, completed.stdout, completed.stderr)

    def ok(self, *args: str, env: Mapping[str, str | None] | None = None) -> CliResult:
        """Run a command that is expected to succeed."""
        result = self(*args, env=env)
        assert result.returncode == 0, f"atlas {' '.join(args)}\n{result.output}"
        return result

    def network_attempts(self) -> list[str]:
        if not self.network_log.exists():
            return []
        return self.network_log.read_text(encoding="utf-8").splitlines()


@pytest.fixture
def cli(tmp_path: Path) -> Cli:
    guard_dir = tmp_path / "_guard"
    guard_dir.mkdir()
    (guard_dir / "sitecustomize.py").write_text(_NETWORK_GUARD, encoding="utf-8")
    cwd = tmp_path / "home"
    cwd.mkdir()
    return Cli(cwd=cwd, network_log=tmp_path / "network.log", _guard_dir=guard_dir)


@pytest.fixture
def project(cli: Cli) -> Callable[[], str]:
    """Create a project and return its ID."""

    def create() -> str:
        return cli.ok(
            "project",
            "create",
            "--name",
            "Offline Demo",
            "--description",
            "Exercise the pipeline with no network.",
            "--objective",
            "Prove every stage works offline.",
        ).first_uuid()

    return create
