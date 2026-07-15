import pytest

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
    with pytest.raises(SystemExit):
        _parse_target(None, None, None)
