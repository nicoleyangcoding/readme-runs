"""readme-runs command line."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import __version__
from .parser import Block, parse
from .runner import DEFAULT_IMAGE, DockerRunner, LocalRunner, RunnerError

TAIL_LINES = 40


def _tail(text: str, lines: int = TAIL_LINES) -> str:
    rows = text.rstrip("\n").splitlines()
    cut = rows[-lines:]
    prefix = [f"... ({len(rows) - lines} earlier lines hidden)"] if len(rows) > lines else []
    return "\n".join("    " + r for r in prefix + cut)


def _missing_command(output: str) -> str | None:
    match = re.search(r"(?:^|\s)([\w.+-]+): (?:command )?not found", output)
    return match.group(1) if match else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="readme-runs",
        description="Run the shell commands in a README, in order, to check that the setup steps still work.",
        epilog=(
            "Examples:\n"
            "  readme-runs\n"
            "  readme-runs docs/INSTALL.md --image python:3.12\n"
            "  readme-runs --list"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", nargs="?", default="README.md", help="Markdown file (default: README.md)")
    parser.add_argument("--image", help=f"Docker image to run in (default: {DEFAULT_IMAGE})")
    parser.add_argument(
        "--local", action="store_true", help="run on this machine in a temp copy, without Docker"
    )
    parser.add_argument("--no-network", action="store_true", help="run the container without network access")
    parser.add_argument(
        "--timeout", type=float, default=300, metavar="SEC", help="per-block limit (default: 300)"
    )
    parser.add_argument("--list", action="store_true", help="show the blocks that would run, then exit")
    parser.add_argument("-v", "--verbose", action="store_true", help="print every block's output")
    parser.add_argument("--version", action="version", version=f"readme-runs {__version__}")
    return parser


def _print_list(blocks: list[Block], skipped: list[int], name: str) -> None:
    for block in blocks:
        print(f"  {block.index:>2}. line {block.line:<5} {block.summary}")
    if skipped:
        print(f"  skipped: line {', '.join(map(str, skipped))}")
    print(f"{len(blocks)} block(s) would run from {name}.")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = Path(args.file)
    try:
        doc = parse(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"readme-runs: {path} not found", file=sys.stderr)
        return 2

    if args.list:
        _print_list(doc.blocks, doc.skipped, path.name)
        return 0
    if not doc.blocks:
        print(f"No bash, sh or console code blocks found in {path}.")
        return 0

    image = args.image or doc.image or DEFAULT_IMAGE
    source = path.resolve().parent
    if args.local:
        runner = LocalRunner(source)
        where = "locally (not isolated)"
    else:
        runner = DockerRunner(source, image, network=not args.no_network)
        where = f"in {image}"
    print(f"Running {len(doc.blocks)} block(s) from {path.name} {where}\n")

    try:
        runner.start()
        for block in doc.blocks:
            outcome = runner.run(block.script, args.timeout)
            status = "ok" if outcome.code == 0 else "FAIL"
            where = f"{block.index:>2}. line {block.line:<5}"
            print(f"  {status:<4}  {where} {block.summary}  ({outcome.seconds:.1f}s)")
            if args.verbose and outcome.output.strip():
                print(_tail(outcome.output, 10_000))
            if outcome.code != 0:
                reason = (
                    f"timed out after {args.timeout:g}s" if outcome.timed_out else f"exit code {outcome.code}"
                )
                print(f"\nBlock {block.index} (line {block.line}) failed: {reason}")
                if outcome.output.strip() and not args.verbose:
                    print(_tail(outcome.output))
                missing = _missing_command(outcome.output)
                if missing and not args.local:
                    print(
                        f"\nHint: '{missing}' isn't installed in {image}. Use an image that has it "
                        "(--image, or <!-- readme-runs: image=IMAGE --> in the README), "
                        "or install it in an earlier README step."
                    )
                return 1
    except RunnerError as exc:
        print(f"readme-runs: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 130
    finally:
        runner.stop()

    print(f"\nAll {len(doc.blocks)} block(s) passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
