# Changelog

All notable changes to this project are documented in this file.

## [0.3.0] — 2026-07-19

### Added

- `--batch FILE` — gate many issues at once (URL / `OWNER/REPO#N` / `OWNER/REPO/issues/N` per line)
- Batch summary table (`GO=` / `STOP=`); exit `1` if any target is STOP
- CLOSED issues: distinguish **fixed** vs **not-planned / duplicate / won't-fix** (`details.closed_as`)

### Changed

- Commit / changelog / release / open-PR matching now requires **explicit** refs (`#N`, `issues/N`, `Fixes #N`) — bare issue numbers no longer count (fewer false STOP)

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
