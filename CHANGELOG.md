# Changelog

All notable changes to this project are documented in this file.

## [0.2.2] — 2026-07-17

### Removed

- Dropped PyPI publishing plans and related docs / `examples/workflows/publish.yml`
- Install path is GitHub archive / `git+https` / pipx / editable only

## [0.2.1] — 2026-07-16

### Added

- README: Users / Developers install (GitHub archive, `git+https`, pipx)
- README: prerequisites (`gh auth`), full CLI help, GO/STOP/ERROR examples, troubleshooting, CI sample
- `examples/github-actions-usage.yml` — copy-paste workflow for pre-contribute gating
- `examples/workflows/ci.yml` — template to enable pytest CI
- This `CHANGELOG.md`

### Notes

- Enable CI by copying `examples/workflows/ci.yml` into `.github/workflows/` (needs a token with `workflow` scope to push that path).

## [0.2.0] — 2026-07-16

### Added

- **STOP** when an open PR already references the target issue
- Report includes `confidence` (HIGH/MEDIUM/LOW) and `open_prs` list
- `--json` output includes the new fields

## [0.1.0] — 2026-07-16

### Added

- Initial MVP: GO/STOP via `gh` (issue state, changelog, releases, default-branch commit search)
- CLI entry points: `upstream-fix-gate`, `ufg`
