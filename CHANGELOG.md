# Changelog

All notable changes to this project are documented in this file.

## [0.2.1] — 2026-07-16

### Added

- README: Users / Developers install (GitHub archive, `git+https`, pipx, planned PyPI)
- README: prerequisites (`gh auth`), full CLI help, GO/STOP/ERROR examples, troubleshooting, CI sample
- `examples/github-actions-usage.yml` — copy-paste workflow for pre-contribute gating
- `examples/workflows/ci.yml` / `publish.yml` — templates to enable pytest CI and tag-based PyPI upload
- This `CHANGELOG.md`

### Notes

- PyPI publish (`pip install upstream-fix-gate`) is prepared in packaging metadata; first upload pending API token.
- Enable CI by copying `examples/workflows/*.yml` into `.github/workflows/` (needs a token with `workflow` scope to push those paths).

## [0.2.0] — 2026-07-16

### Added

- **STOP** when an open PR already references the target issue
- Report includes `confidence` (HIGH/MEDIUM/LOW) and `open_prs` list
- `--json` output includes the new fields

## [0.1.0] — 2026-07-16

### Added

- Initial MVP: GO/STOP via `gh` (issue state, changelog, releases, default-branch commit search)
- CLI entry points: `upstream-fix-gate`, `ufg`
