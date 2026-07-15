"""CLI entrypoint: `upstream-fix-gate` / `ufg`."""

from __future__ import annotations

import argparse
import json
import re
import sys

from upstream_fix_gate.check import GhError, evaluate


def _parse_target(repo: str | None, issue: str | None, url: str | None) -> tuple[str, int]:
    if url:
        m = re.match(
            r"https?://github\.com/([^/]+/[^/]+)/issues/(\d+)/?",
            url.strip(),
        )
        if not m:
            raise SystemExit(f"Unrecognized issue URL: {url}")
        return m.group(1), int(m.group(2))
    if not repo or not issue:
        raise SystemExit("Provide --repo OWNER/NAME --issue N, or --url ISSUE_URL")
    return repo, int(issue)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="upstream-fix-gate",
        description=(
            "Hard gate before OSS contributions: check whether an upstream issue "
            "already looks fixed in releases / changelog / default branch."
        ),
    )
    p.add_argument("--repo", help="Upstream repo as OWNER/NAME")
    p.add_argument("--issue", help="Issue number")
    p.add_argument("--url", help="Full GitHub issue URL")
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        repo, issue = _parse_target(args.repo, args.issue, args.url)
        result = evaluate(repo, issue)
    except GhError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(
            json.dumps(
                {
                    "repo": result.repo,
                    "issue": result.issue,
                    "decision": result.decision,
                    "reasons": result.reasons,
                    "details": result.details,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(result.to_text())

    return 0 if result.decision == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
