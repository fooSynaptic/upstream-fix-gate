"""CLI entrypoint: `upstream-fix-gate` / `ufg`."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from upstream_fix_gate.check import (
    GhError,
    evaluate,
    evaluate_batch,
    format_batch_summary,
    load_batch_targets,
)


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
            "already looks fixed in releases / changelog / default branch, or already "
            "has an open PR claiming it."
        ),
    )
    p.add_argument("--repo", help="Upstream repo as OWNER/NAME")
    p.add_argument("--issue", help="Issue number")
    p.add_argument("--url", help="Full GitHub issue URL")
    p.add_argument(
        "--batch",
        metavar="FILE",
        help=(
            "Batch mode: file with one target per line "
            "(URL, OWNER/REPO#N, or OWNER/REPO/issues/N). "
            "Lines starting with # are comments."
        ),
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.batch:
            if args.repo or args.issue or args.url:
                print(
                    "error: --batch cannot be combined with --repo/--issue/--url",
                    file=sys.stderr,
                )
                return 2
            path = Path(args.batch)
            if not path.is_file():
                print(f"error: batch file not found: {path}", file=sys.stderr)
                return 2
            try:
                targets = load_batch_targets(path)
            except ValueError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
            results = evaluate_batch(targets)
        else:
            repo, issue = _parse_target(args.repo, args.issue, args.url)
            results = [evaluate(repo, issue)]
    except GhError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        if args.batch:
            payload = {
                "batch": True,
                "count": len(results),
                "go": sum(1 for r in results if r.decision == "GO"),
                "stop": sum(1 for r in results if r.decision == "STOP"),
                "results": [r.to_dict() for r in results],
            }
        else:
            payload = results[0].to_dict()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.batch:
        for result in results:
            print(result.to_text())
            print("---")
        print(format_batch_summary(results))
    else:
        print(results[0].to_text())

    if any(r.decision == "STOP" for r in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
