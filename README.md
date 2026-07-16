# upstream-fix-gate

**GO / STOP before you contribute.**

Avoid opening duplicate OSS work when the upstream issue is already fixed in a release, changelog, or default branch — or when **someone already has an open PR** for it.

```bash
pip install -e .
ufg --url https://github.com/OWNER/REPO/issues/123
# or
upstream-fix-gate --repo OWNER/REPO --issue 123
```

Example:

```text
repo:       VectifyAI/PageIndex
issue:      #326
decision:   STOP
confidence: MEDIUM
reasons:
  - Open PR(s) already reference #326: #333 — avoid duplicate work
  - Do not fork / open a duplicate contribution; update your plan status only
open_prs:
  - #333 fix: improve JSON extraction (...)
```

Exit codes: `0` = **GO**, `1` = **STOP**, `2` = tool/auth error.

## What it checks

| Signal | Effect |
|--------|--------|
| Issue `CLOSED` (+ fix-ish language) | STOP lean |
| `CHANGELOG.md` / `HISTORY.md` mentions `#N` | STOP |
| Recent release notes mention `#N` | STOP |
| Default-branch commits mention `N` | STOP lean |
| **Open PR already references `#N`** | **STOP** (new) |
| Confidence `HIGH` / `MEDIUM` / `LOW` | How strong the STOP/GO case is |

Requires [GitHub CLI](https://cli.github.com/) (`gh auth login`).

## Install

```bash
git clone https://github.com/fooSynaptic/upstream-fix-gate.git
cd upstream-fix-gate
pip install -e ".[dev]"
pytest
ufg --help
```

## JSON output

```bash
ufg --repo OWNER/REPO --issue 123 --json
```

Includes `decision`, `confidence`, `reasons`, and `details.open_prs` when present.

## Phase 1 note

This is a **validation MVP** for the fooSynaptic star-growth plan: ship a sharp painkiller, measure conversion, archive if nobody cares.

## License

MIT
