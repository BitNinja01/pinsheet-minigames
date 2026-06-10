## Agent skills

### Issue tracker

Issues live as local markdown files in `.scratch/issues/`. Each file is named `P<priority>_<NNN>_<name>.md` with YAML frontmatter. Priority levels: P0 (critical) through P3 (low). Use `/issue` to manage them.

### Per-project hooks

Project-specific session overrides live in `.opencode/session-start.md` and `.opencode/session-end.md` — read by the global `/session-start` and `/session-end` commands.
