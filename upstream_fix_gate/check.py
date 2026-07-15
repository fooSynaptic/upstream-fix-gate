"""Core GO/STOP checks via the GitHub CLI (`gh`)."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any


class GhError(RuntimeError):
    pass


def _run_gh(args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["gh", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise GhError("`gh` CLI not found. Install GitHub CLI and run `gh auth login`.") from exc
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise GhError(err or f"gh {' '.join(args)} failed ({proc.returncode})")
    return proc.stdout


def _gh_json(args: list[str]) -> Any:
    return json.loads(_run_gh(args))


@dataclass
class CheckResult:
    repo: str
    issue: int
    decision: str  # GO | STOP
    reasons: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_text(self) -> str:
        lines = [
            f"repo:     {self.repo}",
            f"issue:    #{self.issue}",
            f"decision: {self.decision}",
            "reasons:",
        ]
        for reason in self.reasons:
            lines.append(f"  - {reason}")
        return "\n".join(lines) + "\n"


def _issue_mentions_fix(body: str, comments: list[dict]) -> bool:
    blob = (body or "") + "\n" + "\n".join(c.get("body") or "" for c in comments)
    return bool(
        re.search(
            r"(?i)\b(fixed|fix(?:ed)?|shipped|released|merged|already (?:fixed|resolved)|closes?)\b",
            blob,
        )
    )


def _changelog_hits(repo: str, issue: int) -> list[str]:
    hits: list[str] = []
    for path in ("CHANGELOG.md", "CHANGES.md", "HISTORY.md", "docs/CHANGELOG.md"):
        try:
            content = _run_gh(["api", f"repos/{repo}/contents/{path}", "--jq", ".content"])
        except GhError:
            continue
        # content is raw base64 from API unless we decode; prefer raw via -H Accept
        try:
            raw = _run_gh(
                [
                    "api",
                    f"repos/{repo}/contents/{path}",
                    "-H",
                    "Accept: application/vnd.github.raw",
                ]
            )
        except GhError:
            continue
        if re.search(rf"#\s*{issue}\b|issues/{issue}\b", raw):
            hits.append(path)
    return hits


def _release_notes_hits(repo: str, issue: int, limit: int = 8) -> list[str]:
    try:
        releases = _gh_json(
            [
                "api",
                f"repos/{repo}/releases?per_page={limit}",
                "--jq",
                "[.[] | {tag: .tag_name, body: (.body // \"\")}]",
            ]
        )
    except GhError:
        return []
    hits = []
    pattern = re.compile(rf"#\s*{issue}\b|issues/{issue}\b")
    for rel in releases or []:
        body = rel.get("body") or ""
        if pattern.search(body):
            hits.append(rel.get("tag") or "?")
    return hits


def _default_branch_grep(repo: str, issue: int) -> bool:
    """Best-effort: search code for issue number on default branch."""
    try:
        result = _gh_json(
            [
                "search",
                "code",
                "--repo",
                repo,
                str(issue),
                "--json",
                "path",
                "--limit",
                "5",
            ]
        )
        # newer gh: `gh search code` may return list
        if isinstance(result, list) and result:
            return True
        if isinstance(result, dict) and result.get("items"):
            return True
    except GhError:
        pass
    # Fallback: commit messages mentioning the issue
    try:
        out = _run_gh(
            [
                "api",
                f"search/commits?q=repo:{repo}+{issue}",
                "--jq",
                ".total_count",
            ]
        )
        return int(out.strip() or "0") > 0
    except (GhError, ValueError):
        return False


def evaluate(repo: str, issue: int) -> CheckResult:
    """Return GO if contribution still makes sense; STOP if likely already fixed."""
    reasons: list[str] = []
    details: dict[str, Any] = {}

    issue_data = _gh_json(
        [
            "issue",
            "view",
            str(issue),
            "--repo",
            repo,
            "--json",
            "state,title,body,closedAt,comments",
        ]
    )
    state = issue_data.get("state")
    details["issue_state"] = state
    details["title"] = issue_data.get("title")

    comments = issue_data.get("comments") or []
    # gh returns comments as list of objects or sometimes need separate fetch
    if comments and isinstance(comments[0], str):
        comments = [{"body": c} for c in comments]

    stop_signals = 0

    if state == "CLOSED":
        reasons.append(f"Upstream issue #{issue} is CLOSED")
        if _issue_mentions_fix(issue_data.get("body") or "", comments):
            reasons.append("Close discussion / body mentions a fix or release")
            stop_signals += 1
        else:
            reasons.append("Closed — verify whether closed as fixed vs not-planned before contributing")
            stop_signals += 1

    changelog = _changelog_hits(repo, issue)
    if changelog:
        reasons.append(f"Changelog mentions #{issue}: {', '.join(changelog)}")
        details["changelog"] = changelog
        stop_signals += 1

    releases = _release_notes_hits(repo, issue)
    if releases:
        reasons.append(f"Release notes mention #{issue}: {', '.join(releases)}")
        details["releases"] = releases
        stop_signals += 1

    if _default_branch_grep(repo, issue):
        reasons.append("Default-branch code/commits mention this issue number (possible landed fix)")
        details["branch_mention"] = True
        stop_signals += 1

    if stop_signals >= 1 and state == "CLOSED":
        decision = "STOP"
    elif stop_signals >= 2:
        decision = "STOP"
    elif stop_signals == 1 and (changelog or releases):
        decision = "STOP"
    else:
        decision = "GO"
        if not reasons:
            reasons.append("Issue still OPEN and no changelog/release/default-branch hit found")
        else:
            reasons.append("Signals present but not enough to auto-STOP — manually confirm before opening work")

    if decision == "STOP":
        reasons.append("Do not fork / open a duplicate contribution; update your plan status only")
    else:
        reasons.append("Contribution may still be valuable if no equivalent fix exists on default branch")

    return CheckResult(
        repo=repo,
        issue=issue,
        decision=decision,
        reasons=reasons,
        details=details,
    )
