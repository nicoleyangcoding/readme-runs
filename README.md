# readme-runs

Run the shell commands in your README inside a clean container, so you know your setup steps still work.

Install instructions break quietly: a renamed script, a missing dependency, a step that only works on your laptop. New users find out first. `readme-runs` follows your README the way a newcomer would, top to bottom in a fresh environment, and tells you exactly which step fails.

```
$ readme-runs --image python:3.12-slim
Running 3 block(s) from README.md in python:3.12-slim

  ok     1. line 14    python -m venv .venv  (1.4s)
  ok     2. line 21    pip install -r requirements.txt  (6.2s)
  FAIL   3. line 30    python app.py --init  (0.1s)

Block 3 (line 30) failed: exit code 1
    FileNotFoundError: [Errno 2] No such file or directory: 'config.example.toml'
```

## Quick start

Requires Python 3.9+ and Docker, on macOS or Linux.

<!-- readme-runs: skip -->
```bash
pipx install git+https://github.com/nicoleyangcoding/readme-runs
cd your-project
readme-runs
```

## What runs

- Code blocks tagged `bash`, `sh` or `shell` run as scripts.
- In `console` blocks (terminal transcripts), only lines starting with `$ ` run. The output lines are ignored.
- Blocks run in order in **one shell session**. A `cd`, an activated virtualenv or an `export` carries over to later blocks, like in a real terminal.
- Each block stops at its first failing command (`set -e`, plus `pipefail` in bash).
- Commands get no keyboard input, so a prompt fails the step instead of hanging. Add `-y` or similar flags in your README.
- `CI=true` is set, as on most CI systems.

Your project folder is copied into the container. Nothing you run can change your real files. Folders like `node_modules` and `.venv` aren't copied, because they belong to your machine, not to a fresh setup.

## Controlling it from the README

Put HTML comments in your README. They are invisible when rendered.

```markdown
<!-- readme-runs: image=node:24 -->       pick the environment once, for the whole file

<!-- readme-runs: skip -->                skip the next code block
```

Skip blocks that deploy, need secrets, or only make sense on a real machine.

## Options

| Option | What it does |
| --- | --- |
| `readme-runs [FILE]` | Check `FILE` (default `README.md`). |
| `--image IMAGE` | Docker image to start from. Default `ubuntu:24.04`, or the README's `image=` comment. |
| `--list` | Show which blocks would run, without running anything. |
| `-v`, `--verbose` | Print each block's output, not just the failing one. |
| `--timeout SEC` | Time limit per block (default 300). |
| `--no-network` | Run without network access. |
| `--local` | Run on this machine in a temporary copy, without Docker. Not isolated: only use it on READMEs you trust, or on CI machines that are thrown away anyway. |

Exit status is `0` when every block passes, `1` when one fails, and `2` when readme-runs itself couldn't run (no Docker, a bad image, a missing file).

## Use it in GitHub Actions

```yaml
on: [pull_request]
jobs:
  readme:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: nicoleyangcoding/readme-runs@v0
        with:
          image: python:3.12-slim   # optional
```

GitHub's Ubuntu runners include Docker, so no setup is needed.

## Safety

A README can contain any command, so readme-runs runs it in a container by default. Only use `--local` on READMEs you trust. readme-runs doesn't send your project anywhere: the only network traffic is pulling the image and whatever your README's own commands do.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [roadmap](ROADMAP.md).

## License

[MIT](LICENSE)
