# upstream-fix-gate

**GO / STOP before you contribute.**

Avoid opening duplicate OSS work when the upstream issue is already fixed in a release, changelog, or default branch — or when **someone already has an open PR** for it.

```bash
ufg --url https://github.com/OWNER/REPO/issues/123
# or
upstream-fix-gate --repo OWNER/REPO --issue 123
```

Exit codes: `0` = **GO**, `1` = **STOP**, `2` = tool/auth error.

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| Python **≥ 3.9** | Runtime |
| [GitHub CLI](https://cli.github.com/) `gh` | All GitHub calls go through `gh` (not a raw PAT in-process) |
| `gh auth login` | Once per machine; uses your GitHub account / token via the CLI |

No separate `GITHUB_TOKEN` env var is required for local use if `gh` is already authenticated. In CI, use `GH_TOKEN` / `GITHUB_TOKEN` so `gh` can authenticate.

Permissions needed (classic PAT scopes if you use a token with `gh`): at least **`repo`** (private) or public-repo read for public issues/PRs/releases (`public_repo` / fine-grained: Issues + Pull requests + Contents read).

---

## Installation

### Users — no clone (pinned release)

```bash
pip install https://github.com/fooSynaptic/upstream-fix-gate/archive/refs/tags/v0.3.0.tar.gz
```

### Users — no clone (track `main`)

```bash
pip install git+https://github.com/fooSynaptic/upstream-fix-gate.git
# optional pin:
# pip install git+https://github.com/fooSynaptic/upstream-fix-gate.git@main
```

### Users — [pipx](https://pipx.pypa.io/) (isolated CLI)

```bash
pipx install git+https://github.com/fooSynaptic/upstream-fix-gate.git
# or pinned:
# pipx install https://github.com/fooSynaptic/upstream-fix-gate/archive/refs/tags/v0.3.0.tar.gz
```

### Developers

```bash
git clone https://github.com/fooSynaptic/upstream-fix-gate.git
cd upstream-fix-gate
pip install -e ".[dev]"
pytest
ufg --help
```

| Method | Clone needed? | Audience | Editable? |
|--------|---------------|----------|-----------|
| `pip install -e .` | Yes | Contributors | Yes |
| Release `.tar.gz` | No | Users (stable) | No |
| `git+https://…` | No | Users (latest) | No |

---

## Quick examples

### STOP — open PR already claims the issue

```text
$ ufg --url https://github.com/VectifyAI/PageIndex/issues/326
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

### GO — still open, no shipped-fix signal

```text
$ ufg --repo OWNER/REPO --issue 42
repo:       OWNER/REPO
issue:      #42
decision:   GO
confidence: LOW
reasons:
  - Issue still OPEN; no changelog/release/open-PR/default-branch hit found
  - Contribution may still be valuable if no equivalent fix exists on default branch
```

### ERROR — `gh` missing or not logged in

```text
$ ufg --repo OWNER/REPO --issue 1
error: `gh` CLI not found. Install GitHub CLI and run `gh auth login`.
# exit code 2
```

### Batch — many issues in one pass

```bash
# issues.txt (one per line; # starts a comment)
# https://github.com/OWNER/REPO/issues/123
# OWNER/REPO#456
ufg --batch issues.txt
```

Example summary footer:

```text
batch: 3 issue(s) — GO=1 STOP=2

decision conf   target
-------- ------ ----------------------------------------
STOP     MEDIUM VectifyAI/PageIndex#326
GO       LOW    OWNER/REPO#42
STOP     HIGH   acme/tool#7
```

Exit code is `1` if **any** target is STOP (CI-friendly). Use `--batch issues.txt --json` for a machine-readable list.

Sample file: [`examples/issues.batch.txt`](examples/issues.batch.txt).

---

## CLI reference

```text
usage: upstream-fix-gate [-h] [--repo REPO] [--issue ISSUE] [--url URL]
                          [--batch FILE] [--json]

Hard gate before OSS contributions: check whether an upstream issue already
looks fixed in releases / changelog / default branch, or already has an open
PR claiming it.

options:
  -h, --help     show this help message and exit
  --repo REPO    Upstream repo as OWNER/NAME
  --issue ISSUE  Issue number
  --url URL      Full GitHub issue URL
  --batch FILE   Batch file: one URL or OWNER/REPO#N per line
  --json         Emit machine-readable JSON
```

Aliases: `upstream-fix-gate` and `ufg`.

Provide either `--batch FILE`, or `--url`, or both `--repo` and `--issue`.

### JSON output

```bash
ufg --repo OWNER/REPO --issue 123 --json
```

Fields: `decision`, `confidence`, `reasons`, `details` (may include `open_prs`, `changelog`, `releases`, …).

---

## What it checks

| Signal | Effect |
|--------|--------|
| Issue `CLOSED` + fix-ish language | STOP lean (`closed_as=fixed`) |
| Issue `CLOSED` + not-planned / duplicate / won't-fix | STOP (`closed_as=not_planned`) |
| `CHANGELOG.md` / `HISTORY.md` mentions `#N` | STOP |
| Recent release notes mention `#N` | STOP |
| Default-branch commits mention `#N` / `Fixes #N` / `issues/N` | STOP lean |
| Open PR already references `#N` | STOP |
| Confidence `HIGH` / `MEDIUM` / `LOW` | Strength of the case |

**Limits:** uses GitHub’s public API via `gh` — subject to [GitHub rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api). Authenticated `gh` typically gets a higher quota than anonymous calls. Matching requires **explicit** issue refs (`#N`, not a bare number) to cut false positives. This tool does not cache responses yet.

---

## CI example (GitHub Actions)

Gate a workflow before opening contribution work:

```yaml
# .github/workflows/pre-contribute-gate.yml
name: upstream-fix-gate
on:
  workflow_dispatch:
    inputs:
      issue_url:
        description: GitHub issue URL
        required: true

jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install upstream-fix-gate
        run: pip install git+https://github.com/fooSynaptic/upstream-fix-gate.git
      - name: Authenticate gh
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: gh auth status
      - name: Run gate
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: ufg --url "${{ inputs.issue_url }}"
```

A copy-paste sample also lives in [`examples/github-actions-usage.yml`](examples/github-actions-usage.yml).

Ready-to-enable CI workflow (copy into `.github/workflows/`): [`examples/workflows/ci.yml`](examples/workflows/ci.yml).

---

## Troubleshooting

| Symptom | What to do |
|---------|------------|
| `gh` CLI not found | Install from https://cli.github.com/ then retry |
| `gh auth` / HTTP 401 | Run `gh auth login` (or set `GH_TOKEN` in CI) |
| HTTP 403 / rate limit | Wait, or ensure `gh` is authenticated; avoid tight loops |
| `Unrecognized issue URL` | Use `https://github.com/OWNER/REPO/issues/N` |
| Decision looks wrong | Treat as advisory: confirm on the issue/PR page; changelog wording varies by project |
| `pip install …tar.gz` fails | Check tag exists; try `git+https` or a newer tag |

---

## License

MIT
