# upstream-fix-gate

**GO / STOP before you contribute.**

Avoid opening duplicate OSS work when the upstream issue is already fixed in a release, changelog, or default branch — the failure mode we hit when shipping after a released fix.

```bash
pip install -e .
ufg --url https://github.com/OWNER/REPO/issues/123
# or
upstream-fix-gate --repo OWNER/REPO --issue 123
```

Example:

```text
repo:     Dicklesworthstone/destructive_command_guard
issue:    #189
decision: STOP
reasons:
  - Upstream issue #189 is CLOSED
  - Release notes mention #189: v0.6.6
  - Do not fork / open a duplicate contribution; update your plan status only
```

Exit codes: `0` = **GO**, `1` = **STOP**, `2` = tool/auth error.

## What it checks

| Signal | Effect |
|--------|--------|
| Issue `CLOSED` (+ fix-ish language) | STOP lean |
| `CHANGELOG.md` / `HISTORY.md` mentions `#N` | STOP |
| Recent release notes mention `#N` | STOP |
| Default-branch commits/code mention `N` | STOP lean |

Requires [GitHub CLI](https://cli.github.com/) (`gh auth login`).

## Install

```bash
git clone https://github.com/fooSynaptic/upstream-fix-gate.git
cd upstream-fix-gate
pip install -e ".[dev]"
pytest
ufg --help
```

## Phase 1 note

This is a **validation MVP** for the fooSynaptic star-growth plan: ship a sharp painkiller, measure conversion, archive if nobody cares.

## License

MIT
