# claude-skills

A collection of custom [Claude Code](https://claude.com/claude-code) skills, packaged for global installation.

## Layout

Each skill lives in its own top-level directory containing a `SKILL.md` and any supporting files (e.g. `scripts/`).

- [`token-audit/`](token-audit/) — analyzes a Claude Code session transcript to find what drove token/context usage and suggests concrete changes to reduce it.

## Usage

Install all skills globally (available in `~/.claude/skills/`, usable from any project):

```sh
make install
```

This packages every top-level directory containing a `SKILL.md`. To target a single skill:

```sh
make install SKILL=<skill-name>
```

Other targets:

- `make zip [SKILL=<skill-name>]` — package skill(s) into `dist/<skill-name>.zip`
- `make clean` — remove the `dist/` directory
