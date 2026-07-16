from unittest.mock import patch

from upstream_fix_gate.check import (
    CheckResult,
    _confidence,
    _open_prs_for_issue,
    evaluate,
)
from upstream_fix_gate.cli import _parse_target


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
