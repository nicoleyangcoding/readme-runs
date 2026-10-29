from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from readme_runs.cli import main


def docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0


needs_docker = pytest.mark.skipif(not docker_available(), reason="Docker is not available")

STATEFUL = """
```bash
mkdir -p out && cd out
export NAME=world
echo "$NAME" > greeting.txt
```

```console
$ test "$(basename "$PWD")" = out
$ cat greeting.txt
world
$ test -f ../data.txt
```
"""


def write(tmp_path: Path, text: str, name: str = "README.md") -> Path:
    (tmp_path / "data.txt").write_text("x\n")
    path = tmp_path / name
    path.write_text(text)
    return path


def test_local_keeps_directory_and_exports(tmp_path, capsys):
    readme = write(tmp_path, STATEFUL)
    assert main([str(readme), "--local"]) == 0
    assert "All 2 block(s) passed." in capsys.readouterr().out
    assert not (tmp_path / "out").exists()  # ran in a copy


def test_local_stops_at_first_failure(tmp_path, capsys):
    readme = write(
        tmp_path, "```bash\necho one\n```\n\n```bash\necho boom; false\n```\n\n```bash\necho never\n```\n"
    )
    assert main([str(readme), "--local"]) == 1
    out = capsys.readouterr().out
    assert "Block 2 (line 5) failed: exit code 1" in out and "boom" in out and "never" not in out


def test_pipefail_and_errexit(tmp_path):
    readme = write(tmp_path, "```bash\nfalse | cat\necho should not run\n```\n")
    assert main([str(readme), "--local"]) == 1


def test_timeout(tmp_path, capsys):
    readme = write(tmp_path, "```bash\nsleep 20\n```\n")
    assert main([str(readme), "--local", "--timeout", "1"]) == 1
    assert "timed out after 1s" in capsys.readouterr().out


def test_stdin_is_closed(tmp_path):
    readme = write(tmp_path, "```bash\nread -r answer || echo no input\n```\n")
    assert main([str(readme), "--local", "--timeout", "5"]) == 0


def test_list_and_missing_file(tmp_path, capsys):
    readme = write(tmp_path, STATEFUL)
    assert main([str(readme), "--list"]) == 0
    assert "2 block(s) would run" in capsys.readouterr().out
    assert main([str(tmp_path / "nope.md")]) == 2


def test_no_blocks(tmp_path, capsys):
    readme = write(tmp_path, "# Nothing to run\n")
    assert main([str(readme), "--local"]) == 0
    assert "No bash" in capsys.readouterr().out


@needs_docker
def test_docker_end_to_end(tmp_path, capsys):
    readme = write(tmp_path, STATEFUL)
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "skip.txt").write_text("x")
    assert main([str(readme), "--image", "alpine:3.20"]) == 0


@needs_docker
def test_docker_missing_command_hint(tmp_path, capsys):
    readme = write(tmp_path, "```bash\nnot-a-real-tool --version\n```\n")
    assert main([str(readme), "--image", "alpine:3.20"]) == 1
    assert "Hint: 'not-a-real-tool' isn't installed" in capsys.readouterr().out


@needs_docker
def test_docker_bad_image(tmp_path, capsys):
    readme = write(tmp_path, "```bash\necho hi\n```\n")
    assert main([str(readme), "--image", "readme-runs/does-not-exist:0"]) == 2
    assert "Couldn't start image" in capsys.readouterr().err
