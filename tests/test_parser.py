from readme_runs.parser import parse

README = """# Project

Install:

```bash
pip install .
make build
```

```console
$ ./run --check
All good
$ export MODE=fast \\
    LEVEL=2
done
```

<!-- readme-runs: skip -->
```sh
rm -rf ~/
```

```python
print("not shell")
```

~~~shell
echo tilde fence
~~~

````bash
echo four backticks
```
still inside
````

    ```bash
    indented code is not a fence
    ```
"""


def test_finds_runnable_blocks_in_order():
    doc = parse(README)
    assert [b.line for b in doc.blocks] == [5, 10, 27, 31]
    assert doc.blocks[0].script == "pip install .\nmake build\n"
    assert [b.index for b in doc.blocks] == [1, 2, 3, 4]


def test_console_keeps_only_prompted_commands_and_continuations():
    block = parse(README).blocks[1]
    assert block.script == "./run --check\nexport MODE=fast \\\n    LEVEL=2\n"


def test_skip_directive_and_non_shell_languages():
    doc = parse(README)
    assert doc.skipped == [19]
    assert all("rm -rf" not in b.script for b in doc.blocks)
    assert all("print(" not in b.script for b in doc.blocks)


def test_longer_fences_contain_shorter_ones():
    block = parse(README).blocks[3]
    assert "still inside" in block.script


def test_prompts_inside_bash_block():
    doc = parse("```bash\n$ make\nmake: done\n$ make test\n```\n")
    assert doc.blocks[0].script == "make\nmake test\n"


def test_image_directive():
    assert parse("<!-- readme-runs: image=node:24 -->\n").image == "node:24"
    assert parse("<!-- README-RUNS: image = python:3.12 -->").image == "python:3.12"
    assert parse("nothing here").image is None


def test_skip_only_applies_to_the_next_block():
    doc = parse("<!-- readme-runs: skip -->\n\n```bash\na\n```\n\n```bash\nb\n```\n")
    assert [b.script for b in doc.blocks] == ["b\n"]


def test_unclosed_fence_and_empty_blocks():
    assert parse("```bash\n```\n").blocks == []
    assert parse("```bash\necho unclosed\n").blocks[0].script == "echo unclosed\n"


def test_summary_truncates():
    block = parse("```bash\n\n" + "x" * 100 + "\n```").blocks[0]
    assert len(block.summary) == 60 and block.summary.endswith("...")
