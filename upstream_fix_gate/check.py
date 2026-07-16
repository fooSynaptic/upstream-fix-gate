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
    out = _run_gh(args)
    if not out.strip():
        return None
    return json.loads(out)


@dataclass
class CheckResult:
    repo: str
    issue: int
    decision: str  # GO | STOP
    confidence: str = "LOW"  # HIGH | MEDIUM | LOW
    reasons: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_text(self) -> str:
        lines = [
            f"repo:       {self.repo}",
            f"issue:      #{self.issue}",
            f"decision:   {self.decision}",
            f"confidence: {self.confidence}",
            "reasons:",
        ]
        for reason in self.reasons:
            lines.append(f"  - {reason}")
        open_prs = self.details.get("open_prs") or []
        if open_prs:
            lines.append("open_prs:")
            for pr in open_prs:
                lines.append(
                    f"  - #{pr.get('number')} {pr.get('title')} ({pr.get('url')})"
                )
        return "\n".join(lines) + "\n"


def _issue_mentions_fix(body: str, comments: list[dict]) -> bool:
    blob = (body or "") + "\n" + "\n".join(c.get("body") or "" for c in comments)
    return bool(
        re.search(
            r"(?i)\b(fixed|fix(?:ed)?|shipped|released|merged|already (?:fixed|resolved)|closes?)\b",
            blob,
        )
    )


def _normalize_comments(comments: Any) -> list[dict]:
    if not comments:
        return []
    if isinstance(comments, list) and comments and isinstance(comments[0], str):
        return [{"body": c} for c in comments]
    if isinstance(comments, list):
        return [c for c in comments if isinstance(c, dict)]
    return []


def _changelog_hits(repo: str, issue: int) -> list[str]:
    hits: list[str] = []
    for path in ("CHANGELOG.md", "CHANGES.md", "HISTORY.md", "docs/CHANGELOG.md"):
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
                '[.[] | {tag: .tag_name, body: (.body // "")}]',
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
    """Best-effort: search commits for the issue number on the repo."""
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


def _open_prs_for_issue(repo: str, issue: int) -> list[dict[str, Any]]:
    """Find open PRs that reference this issue (title/body/closing keywords)."""
    query = f"repo:{repo} is:pr is:open ({issue} OR #{issue})"
    try:
        items = _gh_json(
            [
                "search",
                "prs",
                query,
                "--json",
                "number,title,url,body",
                "--limit",
                "20",
            ]
        )
    except GhError:
        return []

    if not isinstance(items, list):
        return []

    pattern = re.compile(
        rf"(?i)(?:\b(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s+)?#{issue}\b|"
        rf"issues/{issue}\b|"
        rf"(?<!\d){issue}(?!\d)"
    )
    matched: list[dict[str, Any]] = []
    for item in items:
        title = item.get("title") or ""
        body = item.get("body") or ""
        if pattern.search(title) or pattern.search(body):
            matched.append(
                {
                    "number": item.get("number"),
                    "title": title,
                    "url": item.get("url"),
                }
            )
    return matched


def _confidence(stop_signals: int, state: str, has_shipped: bool, has_open_pr: bool) -> str:
    if state == "CLOSED" and has_shipped:
        return "HIGH"
    if has_shipped or (has_open_pr and stop_signals >= 2):
        return "HIGH"
    if stop_signals >= 2 or has_open_pr or state == "CLOSED":
        return "MEDIUM"
    return "LOW"


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

    comments = _normalize_comments(issue_data.get("comments"))

    stop_signals = 0
    has_shipped = False

    if state == "CLOSED":
        reasons.append(f"Upstream issue #{issue} is CLOSED")
        if _issue_mentions_fix(issue_data.get("body") or "", comments):
            reasons.append("Close discussion / body mentions a fix or release")
        else:
            reasons.append(
                "Closed — verify whether closed as fixed vs not-planned before contributing"
            )
        stop_signals += 1

    changelog = _changelog_hits(repo, issue)
    if changelog:
        reasons.append(f"Changelog mentions #{issue}: {', '.join(changelog)}")
        details["changelog"] = changelog
        stop_signals += 1
        has_shipped = True

    releases = _release_notes_hits(repo, issue)
    if releases:
        reasons.append(f"Release notes mention #{issue}: {', '.join(releases)}")
        details["releases"] = releases
        stop_signals += 1
        has_shipped = True

    if _default_branch_grep(repo, issue):
        reasons.append(
            "Default-branch commits mention this issue number (possible landed fix)"
        )
        details["branch_mention"] = True
        stop_signals += 1

    open_prs = _open_prs_for_issue(repo, issue)
    if open_prs:
        details["open_prs"] = open_prs
        pr_refs = ", ".join(f"#{p['number']}" for p in open_prs)
        reasons.append(
            f"Open PR(s) already reference #{issue}: {pr_refs} — avoid duplicate work"
        )
        stop_signals += 1

    if stop_signals >= 1 and state == "CLOSED":
        decision = "STOP"
    elif has_shipped:
        decision = "STOP"
    elif open_prs and stop_signals >= 1:
        # Open PR alone is enough to STOP: the lane is already taken.
        decision = "STOP"
    elif stop_signals >= 2:
        decision = "STOP"
    else:
        decision = "GO"
        if not reasons:
            reasons.append(
                "Issue still OPEN; no changelog/release/open-PR/default-branch hit found"
            )
        else:
            reasons.append(
                "Signals present but not enough to auto-STOP — manually confirm before opening work"
            )

    confidence = _confidence(stop_signals, state or "", has_shipped, bool(open_prs))

    if decision == "STOP":
        reasons.append(
            "Do not fork / open a duplicate contribution; update your plan status only"
        )
    else:
        reasons.append(
            "Contribution may still be valuable if no equivalent fix exists on default branch"
        )

    return CheckResult(
        repo=repo,
        issue=issue,
        decision=decision,
        confidence=confidence,
        reasons=reasons,
        details=details,
    )
