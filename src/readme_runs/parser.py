"""Find runnable shell blocks in a Markdown file."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SCRIPT_LANGS = {"bash", "sh", "shell"}
SESSION_LANGS = {"console", "shell-session", "shellsession", "terminal"}

_FENCE = re.compile(r"^( {0,3})(`{3,}|~{3,})\s*([^`\s]*)[^`]*$")
_DIRECTIVE = re.compile(r"<!--\s*readme-runs:\s*(.*?)\s*-->", re.IGNORECASE)
_PROMPT = re.compile(r"^\s*\$ ")


@dataclass(frozen=True)
class Block:
    index: int  # 1-based position among runnable blocks
    line: int  # 1-based line of the opening fence
    lang: str
    script: str

    @property
    def summary(self) -> str:
        first = next((ln.strip() for ln in self.script.splitlines() if ln.strip()), "")
        return first if len(first) <= 60 else first[:57] + "..."


@dataclass
class Document:
    blocks: list[Block] = field(default_factory=list)
    skipped: list[int] = field(default_factory=list)  # fence line numbers
    image: str | None = None


def _directives(text: str) -> list[str]:
    return [d.strip().lower() for m in _DIRECTIVE.finditer(text) for d in m.group(1).split(",")]


def _session_commands(body: list[str]) -> str:
    """Keep only '$ command' lines (and their backslash continuations) from a terminal transcript."""
    commands: list[str] = []
    continuing = False
    for line in body:
        if _PROMPT.match(line):
            command = _PROMPT.sub("", line, count=1)
            commands.append(command)
            continuing = command.rstrip().endswith("\\")
        elif continuing:
            commands.append(line)
            continuing = line.rstrip().endswith("\\")
    return "\n".join(commands)


def parse(markdown: str) -> Document:
    doc = Document()
    for match in _DIRECTIVE.finditer(markdown):
        for part in match.group(1).split(","):
            key, _, value = part.strip().partition("=")
            if key.strip().lower() == "image" and value.strip():
                doc.image = value.strip()

    lines = markdown.splitlines()
    i = 0
    last_text = ""  # most recent non-blank line outside a block
    while i < len(lines):
        opening = _FENCE.match(lines[i])
        if not opening:
            if lines[i].strip():
                last_text = lines[i]
            i += 1
            continue
        fence, lang = opening.group(2), opening.group(3).lower()
        start = i
        body: list[str] = []
        i += 1
        while i < len(lines):
            closing = re.match(rf"^ {{0,3}}{fence[0]}{{{len(fence)},}}\s*$", lines[i])
            if closing:
                break
            body.append(lines[i])
            i += 1
        i += 1  # past the closing fence (or end of file)

        if lang not in SCRIPT_LANGS | SESSION_LANGS:
            last_text = ""
            continue
        if "skip" in _directives(last_text):
            doc.skipped.append(start + 1)
            last_text = ""
            continue
        last_text = ""

        prompt_style = lang in SESSION_LANGS or any(_PROMPT.match(b) for b in body)
        script = _session_commands(body) if prompt_style else "\n".join(body)
        if not script.strip():
            continue
        doc.blocks.append(Block(len(doc.blocks) + 1, start + 1, lang, script.strip("\n") + "\n"))
    return doc
