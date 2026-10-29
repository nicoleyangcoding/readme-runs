"""Run blocks one after another in a single, persistent shell session.

Each block runs through a small wrapper that restores the previous block's working
directory and exported variables, then saves them again on exit. That makes a
README behave like someone typing it into one terminal.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

DEFAULT_IMAGE = "ubuntu:24.04"
# Local environments built on the host would be wrong (or huge) inside a fresh environment.
SKIP_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".tox", ".mypy_cache", ".pytest_cache"}
_SKIP_COPY = shutil.ignore_patterns(*SKIP_DIRS)

WRAPPER = r"""
state="$RR_STATE"
cd "$(cat "$state/cwd" 2>/dev/null || echo "$RR_WORK")"
[ -f "$state/env" ] && . "$state/env" >/dev/null 2>&1
save() {
  pwd > "$state/cwd"
  export -p | grep -vE '^(declare -x|export) (PWD|OLDPWD|SHLVL|_|RR_STATE|RR_WORK|HOME|HOSTNAME)=' \
    > "$state/env" || true
}
trap save EXIT
set -e
if [ -n "$BASH_VERSION" ]; then set -o pipefail; fi
. "$state/block.sh"
"""


class RunnerError(Exception):
    pass


@dataclass(frozen=True)
class Outcome:
    code: int
    output: str
    seconds: float
    timed_out: bool = False


class DockerRunner:
    def __init__(self, source: Path, image: str = DEFAULT_IMAGE, network: bool = True):
        self.source, self.image, self.network = source, image, network
        self.name = f"readme-runs-{uuid.uuid4().hex[:10]}"
        self.shell = "sh"

    def _docker(self, *args: str, input_text: str | None = None, timeout: float | None = None):
        return subprocess.run(
            ["docker", *args],
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def start(self) -> None:
        if not shutil.which("docker"):
            raise RunnerError("Docker isn't installed or isn't on PATH. Install Docker, or use --local.")
        if self._docker("version", "--format", "{{.Server.Version}}").returncode != 0:
            raise RunnerError("Docker is installed but not running. Start Docker, or use --local.")
        args = ["run", "-d", "--rm", "--name", self.name]
        args += ["-e", "RR_STATE=/tmp/readme-runs", "-e", "RR_WORK=/work", "-e", "CI=true"]
        if not self.network:
            args += ["--network", "none"]
        result = self._docker(*args, "--entrypoint", "sleep", self.image, "infinity", timeout=600)
        if result.returncode != 0:
            raise RunnerError(f"Couldn't start image '{self.image}': {result.stderr.strip()}")
        found = self._docker(
            "exec", self.name, "sh", "-c", "mkdir -p /tmp/readme-runs /work; command -v bash || true"
        )
        if found.returncode != 0:
            raise RunnerError(f"Couldn't prepare the container: {found.stderr.strip()}")
        self._copy_project()
        self.shell = "bash" if found.stdout.strip() else "sh"
        self._docker(
            "exec", "-i", self.name, "sh", "-c", "cat > /tmp/readme-runs/wrapper.sh", input_text=WRAPPER
        )

    def _copy_project(self) -> None:
        # Stream a tar instead of bind-mounting: works with remote Docker and VMs that only share $HOME.
        with tempfile.TemporaryFile() as archive:
            with tarfile.open(fileobj=archive, mode="w") as tar:
                tar.add(self.source, arcname=".", filter=_tar_filter)
            archive.seek(0)
            result = subprocess.run(
                ["docker", "cp", "-", f"{self.name}:/work"], stdin=archive, capture_output=True, check=False
            )
        if result.returncode != 0:
            message = result.stderr.decode("utf-8", "replace").strip()
            raise RunnerError(f"Couldn't copy the project into the container: {message}")

    def run(self, script: str, timeout: float) -> Outcome:
        self._docker(
            "exec", "-i", self.name, "sh", "-c", "cat > /tmp/readme-runs/block.sh", input_text=script
        )
        began = time.monotonic()
        try:
            result = subprocess.run(
                ["docker", "exec", "-w", "/work", self.name, self.shell, "/tmp/readme-runs/wrapper.sh"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            self.stop()
            return Outcome(124, _text(exc.output), time.monotonic() - began, timed_out=True)
        return Outcome(result.returncode, result.stdout, time.monotonic() - began)

    def stop(self) -> None:
        self._docker("rm", "-f", self.name)


class LocalRunner:
    """Runs on this machine in a temporary copy of the project. Not isolated."""

    def __init__(self, source: Path):
        self.source = source
        self.temp = Path(tempfile.mkdtemp(prefix="readme-runs-"))
        self.work = self.temp / "work"
        self.state = self.temp / "state"
        self.shell = shutil.which("bash") or shutil.which("sh") or "sh"

    def start(self) -> None:
        shutil.copytree(self.source, self.work, symlinks=True, ignore=_SKIP_COPY)
        self.state.mkdir()
        (self.state / "wrapper.sh").write_text(WRAPPER, encoding="utf-8")

    def run(self, script: str, timeout: float) -> Outcome:
        (self.state / "block.sh").write_text(script, encoding="utf-8")
        env = {**os.environ, "RR_STATE": str(self.state), "RR_WORK": str(self.work), "CI": "true"}
        began = time.monotonic()
        proc = subprocess.Popen(
            [self.shell, str(self.state / "wrapper.sh")],
            cwd=self.work,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            start_new_session=True,
        )
        try:
            output, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            output, _ = proc.communicate()
            return Outcome(124, output, time.monotonic() - began, timed_out=True)
        return Outcome(proc.returncode, output, time.monotonic() - began)

    def stop(self) -> None:
        shutil.rmtree(self.temp, ignore_errors=True)


def _tar_filter(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    if any(part in SKIP_DIRS for part in Path(info.name).parts):
        return None
    info.uid = info.gid = 0
    info.uname = info.gname = "root"
    return info


def _text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value or ""
