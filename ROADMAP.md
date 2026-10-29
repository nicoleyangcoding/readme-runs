# Roadmap

Small, focused releases. Suggestions are welcome in [issues](https://github.com/nicoleyangcoding/readme-runs/issues).

## 0.2
- [ ] `<!-- readme-runs: expect-fail -->` for blocks that are supposed to fail
- [ ] `--from N` to start at a given block (with earlier blocks still run silently for setup)
- [ ] Check `console` output lines against real output (opt-in)

## 0.3
- [ ] `<!-- readme-runs: env NAME=value -->` to set variables without changing the README
- [ ] Run several Markdown files in one go (`readme-runs docs/*.md`)
- [ ] JUnit XML report for CI dashboards

## Later
- [ ] Podman support
- [ ] Publish to PyPI so `pipx install readme-runs` works
