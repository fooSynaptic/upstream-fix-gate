from pathlib import Path
from unittest.mock import patch

from upstream_fix_gate.check import (
    CheckResult,
    _confidence,
    _default_branch_grep,
    _issue_looks_not_planned,
    _issue_ref_pattern,
    _open_prs_for_issue,
    evaluate,
    format_batch_summary,
    load_batch_targets,
    parse_batch_line,
)
from upstream_fix_gate.cli import _parse_target, main


def test_parse_url():
    repo, issue = _parse_target(
        None,
        None,
        "https://github.com/VectifyAI/PageIndex/issues/15",
    )
    assert repo == "VectifyAI/PageIndex"
    assert issue == 15


def test_parse_repo_issue():
    repo, issue = _parse_target("foo/bar", "9", None)
    assert repo == "foo/bar"
    assert issue == 9


def test_parse_requires_args():
    try:
        _parse_target(None, None, None)
        assert False, "expected SystemExit"
    except SystemExit:
        pass


def test_confidence_high_when_closed_and_shipped():
    assert _confidence(2, "CLOSED", True, False) == "HIGH"


def test_confidence_medium_when_open_pr():
    assert _confidence(1, "OPEN", False, True) == "MEDIUM"


def test_confidence_high_when_not_planned():
    assert _confidence(1, "CLOSED", False, False, not_planned=True) == "HIGH"


def test_issue_ref_pattern_rejects_bare_number():
    pat = _issue_ref_pattern(15)
    assert pat.search("Fixes #15")
    assert pat.search("see issues/15 for details")
    assert pat.search("#15 landed")
    assert not pat.search("build 15 failed")
    assert not pat.search("python3.15")


def test_not_planned_detection():
    assert _issue_looks_not_planned("Closing as not planned.", [], "wontfix")
    assert _issue_looks_not_planned("duplicate of #9", [], "")
    assert not _issue_looks_not_planned("Fixed in v1.2.3", [], "")


def test_open_prs_filters_by_issue_ref():
    fake = [
        {
            "number": 333,
            "title": "fix: improve JSON extraction",
            "url": "https://github.com/VectifyAI/PageIndex/pull/333",
            "body": "Related to #326",
        },
        {
            "number": 999,
            "title": "unrelated",
            "url": "https://github.com/VectifyAI/PageIndex/pull/999",
            "body": "no issue link here",
        },
    ]
    with patch("upstream_fix_gate.check._gh_json", return_value=fake):
        matched = _open_prs_for_issue("VectifyAI/PageIndex", 326)
    assert len(matched) == 1
    assert matched[0]["number"] == 333


def test_evaluate_stops_on_open_pr():
    issue_payload = {
        "state": "OPEN",
        "title": "Bug/Fix: extract_json",
        "body": "repro",
        "closedAt": None,
        "comments": [],
    }
    open_prs = [
        {
            "number": 333,
            "title": "fix json",
            "url": "https://github.com/VectifyAI/PageIndex/pull/333",
        }
    ]

    with (
        patch("upstream_fix_gate.check._gh_json", return_value=issue_payload),
        patch("upstream_fix_gate.check._changelog_hits", return_value=[]),
        patch("upstream_fix_gate.check._release_notes_hits", return_value=[]),
        patch("upstream_fix_gate.check._default_branch_grep", return_value=False),
        patch("upstream_fix_gate.check._open_prs_for_issue", return_value=open_prs),
    ):
        result = evaluate("VectifyAI/PageIndex", 326)

    assert isinstance(result, CheckResult)
    assert result.decision == "STOP"
    assert result.confidence in {"MEDIUM", "HIGH"}
    assert result.details["open_prs"][0]["number"] == 333
    text = result.to_text()
    assert "open_prs:" in text
    assert "#333" in text


def test_evaluate_closed_not_planned():
    issue_payload = {
        "state": "CLOSED",
        "title": "Feature request",
        "body": "Closing as not planned — out of scope.",
        "closedAt": "2026-01-01",
        "comments": [],
    }
    with (
        patch("upstream_fix_gate.check._gh_json", return_value=issue_payload),
        patch("upstream_fix_gate.check._changelog_hits", return_value=[]),
        patch("upstream_fix_gate.check._release_notes_hits", return_value=[]),
        patch("upstream_fix_gate.check._default_branch_grep", return_value=False),
        patch("upstream_fix_gate.check._open_prs_for_issue", return_value=[]),
    ):
        result = evaluate("acme/tool", 7)

    assert result.decision == "STOP"
    assert result.details.get("closed_as") == "not_planned"
    assert any("not-planned" in r.lower() or "won't-fix" in r.lower() for r in result.reasons)


def test_default_branch_grep_uses_explicit_query():
    with patch("upstream_fix_gate.check._run_gh", return_value="1") as run:
        assert _default_branch_grep("acme/tool", 42) is True
    args = run.call_args[0][0]
    joined = " ".join(args)
    assert "#42" in joined or '"#42"' in joined
    # Must not use bare +42 style that matches any commit containing 42
    assert "+42" not in joined or "#42" in joined


def test_parse_batch_line_variants():
    assert parse_batch_line("https://github.com/a/b/issues/3") == ("a/b", 3)
    assert parse_batch_line("a/b#3") == ("a/b", 3)
    assert parse_batch_line("a/b/issues/3") == ("a/b", 3)
    assert parse_batch_line("# comment") is None
    assert parse_batch_line("  ") is None


def test_load_batch_targets(tmp_path: Path):
    f = tmp_path / "issues.txt"
    f.write_text(
        "# plan\n"
        "https://github.com/VectifyAI/PageIndex/issues/15\n"
        "acme/tool#9\n"
        "acme/tool#9\n"
        "\n",
        encoding="utf-8",
    )
    targets = load_batch_targets(f)
    assert targets == [("VectifyAI/PageIndex", 15), ("acme/tool", 9)]


def test_format_batch_summary():
    results = [
        CheckResult("a/b", 1, "GO", "LOW", ["ok"]),
        CheckResult("a/b", 2, "STOP", "HIGH", ["done"]),
    ]
    text = format_batch_summary(results)
    assert "GO=1 STOP=1" in text
    assert "a/b#1" in text
    assert "a/b#2" in text


def test_main_batch_exit_stop(tmp_path: Path):
    f = tmp_path / "batch.txt"
    f.write_text("acme/tool#1\n", encoding="utf-8")
    fake = CheckResult("acme/tool", 1, "STOP", "MEDIUM", ["open pr"])
    with patch("upstream_fix_gate.cli.evaluate_batch", return_value=[fake]):
        code = main(["--batch", str(f)])
    assert code == 1


def test_main_batch_exit_go(tmp_path: Path):
    f = tmp_path / "batch.txt"
    f.write_text("acme/tool#1\n", encoding="utf-8")
    fake = CheckResult("acme/tool", 1, "GO", "LOW", ["clear"])
    with patch("upstream_fix_gate.cli.evaluate_batch", return_value=[fake]):
        code = main(["--batch", str(f)])
    assert code == 0
