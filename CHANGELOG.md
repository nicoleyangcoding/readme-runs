# Changelog

All notable changes are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-11-22

### Added
- `<!-- readme-runs: env NAME=value -->` to set a variable for every block
- `--from N` to start at a given block, with earlier blocks still run quietly for setup

## [0.2.0] - 2026-11-11

### Added
- `<!-- readme-runs: expect-fail -->` for blocks that are supposed to fail

## [0.1.0] - 2026-10-29

### Added
- Run `bash`, `sh` and `shell` blocks, and `$ ` lines from `console` blocks, in order
- One persistent shell session: directory, virtualenv and exported variables carry over
- Docker isolation with a copy of the project, plus `--local` mode
- README comments: `image=` and `skip`
- `--list`, `--verbose`, `--timeout` and `--no-network`
- GitHub Action
