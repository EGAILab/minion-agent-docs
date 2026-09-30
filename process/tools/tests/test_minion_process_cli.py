"""CLI surface and remaining failure branches of `minion_process`."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from minion_process import github as github_module
from minion_process.cli import main
from minion_process.github import GitHub, GitHubError, gh_runner
from minion_process.model import BodyFormatError, IssueBody
from minion_process.ops import CheckFailed, candidate_report, commit_state, guarded_merge, verified_comment
from minion_process.transitions import check_transition
from minion_process.validate import errors, validate_workflow

from .test_minion_process import CODE, DOCS, SHA_A, FakeGitHub, workflow


def run(fake: FakeGitHub, *argv: str) -> int:
    return main(list(argv), gh=GitHub(fake.run))


def test_status_validate_and_checks(fake: FakeGitHub, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(fake, "status", "10") == 0
    assert run(fake, "validate", "10") == 0
    assert run(fake, "handoff-check", "10") == 0
    assert run(fake, "candidate-check", "10", "--ready") == 0
    out = capsys.readouterr().out
    assert "WP-X: IMPLEMENTATION_REVIEW" in out and out.count("OK") == 2
    fake.prs[(CODE, 1)]["headRefOid"] = "c" * 40
    assert run(fake, "candidate-check", "10") == 1
    assert run(fake, "handoff-check", "10") == 1
    assert "HANDOFF_BLOCKED" in capsys.readouterr().out


def test_validate_needs_a_source() -> None:
    with pytest.raises(SystemExit):
        main(["validate"])


def test_apply_dry_run_and_failure(
    fake: FakeGitHub, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    patch = tmp_path / "p.py"
    patch.write_text("ALLOWED = {'status'}\ndef apply(w):\n    w['status'] = 'CLOSED'\n", encoding="utf-8")
    assert run(fake, "apply", "10", str(patch)) == 1
    assert "illegal transition" in capsys.readouterr().err
    patch.write_text("ALLOWED = set()\ndef apply(w):\n    return 'new prose'\n", encoding="utf-8")
    assert run(fake, "apply", "10", str(patch), "--dry-run") == 0
    assert "DRY-RUN OK" in capsys.readouterr().out


def test_merge_and_comment_commands(
    fake: FakeGitHub, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(fake, "merge", "code", "1", SHA_A) == 0
    note = tmp_path / "c.md"
    note.write_text("hello\n", encoding="utf-8")
    assert run(fake, "comment", "docs", "2", str(note), "--pr") == 0
    assert "byte-verified" in capsys.readouterr().out


# --- remaining validation / transition / model branches -----------------------------------------


@pytest.mark.parametrize(
    ("overrides", "path"),
    [
        ({"code": "abc"}, "code"),
        ({"convergence": {"open_findings": "R1"}}, "convergence.open_findings"),
        ({"convergence": {"checkpoint": 3}}, "convergence.checkpoint"),
        ({"governance_source": 5}, "governance_source"),
        ({"status": "WAITING_FOR_TRIGGER", "next_owner": None, "next_action": None}, "deferred_trigger"),
    ],
)
def test_more_structural_errors(overrides: dict[str, Any], path: str) -> None:
    assert path in [p.path for p in errors(validate_workflow(workflow(**overrides)))]


def test_unknown_current_status_and_missing_workflow() -> None:
    assert check_transition("BLOCKED", "SCOPING")
    assert check_transition("SCOPING", "NOPE")
    with pytest.raises(BodyFormatError):
        IssueBody(state={"other": 1}, prose="").workflow  # noqa: B018


def test_a_merged_candidate_skips_the_pr_checks(fake: FakeGitHub) -> None:
    w = workflow(code={"pr": 1, "sha": SHA_A, "merged_sha": "m" * 40})
    fake.prs[(CODE, 1)]["state"] = "MERGED"
    assert candidate_report(GitHub(fake.run), w, require_ready=True).failed == []


# --- remaining failure branches of the operations ---------------------------------------------


def _remote_rewrites(fake: FakeGitHub, rewrite: Any) -> GitHub:
    original = fake.run

    def run(args: list[str], stdin: str | None) -> str:
        if args[:2] == ["issue", "edit"] and stdin is not None:
            stdin = rewrite(stdin)
        return original(args, stdin)

    return GitHub(run)


def _handoff(w: dict[str, Any]) -> None:
    w["next_action"] = "changed"


@pytest.mark.parametrize(
    ("rewrite", "match"),
    [
        (lambda body: body.replace("next_action: changed", "next_action: other"), "semantically equal"),
        (lambda body: body + "\nextra prose", "differs from the written body"),
        (lambda body: body.replace("next_owner: Codex", "next_owner: null"), "remote state invalid"),
    ],
)
def test_remote_divergence_is_a_failed_commit(fake: FakeGitHub, rewrite: Any, match: str) -> None:
    with pytest.raises(CheckFailed, match=match):
        commit_state(_remote_rewrites(fake, rewrite), CODE, 10, _handoff, {"next_action"})


def test_a_candidate_without_a_sha_or_side_is_skipped(fake: FakeGitHub) -> None:
    w = workflow(code={"pr": 1}, docs=None)
    assert candidate_report(GitHub(fake.run), w, require_ready=True).failed == []
    assert errors(validate_workflow(w)) == []


def test_merge_waits_for_mergeability_and_detects_a_failed_merge(fake: FakeGitHub) -> None:
    calls = {"n": 0}
    original = fake.run

    def run(args: list[str], stdin: str | None) -> str:
        if args[:2] == ["pr", "view"]:
            calls["n"] += 1
            if calls["n"] == 1:
                fake.prs[(CODE, 1)]["mergeable"] = "UNKNOWN"
            elif calls["n"] == 2:
                fake.prs[(CODE, 1)]["mergeable"] = "MERGEABLE"
        if args[:2] == ["pr", "merge"]:
            return ""  # merge silently did nothing
        return original(args, stdin)

    waits: list[float] = []
    with pytest.raises(CheckFailed, match="did not merge"):
        guarded_merge(GitHub(run), CODE, 1, SHA_A, wait=waits.append)
    assert waits == [3]


def test_a_mangled_comment_is_detected(fake: FakeGitHub) -> None:
    original = fake.run

    def run(args: list[str], stdin: str | None) -> str:
        return original(args, (stdin or "").upper() if args[1] == "comment" else stdin)

    with pytest.raises(CheckFailed, match="differs"):
        verified_comment(GitHub(run), CODE, 10, "lower case\n")


def test_gh_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        code = 0 if cmd[1] == "ok" else 1
        return subprocess.CompletedProcess(cmd, code, stdout="out", stderr="boom")

    monkeypatch.setattr(github_module.subprocess, "run", fake_run)
    assert gh_runner(["ok"], None) == "out"
    with pytest.raises(GitHubError, match="boom"):
        gh_runner(["bad"], "stdin")
    assert DOCS.endswith("docs")


def test_legacy_mapping_findings_warn_in_v1_and_fail_in_v2() -> None:
    legacy = workflow(open_findings={"R1": {"state": "OPEN"}})
    problems = validate_workflow(legacy)
    assert errors(problems) == [] and [p.path for p in problems] == ["open_findings"]
    assert errors(validate_workflow({**legacy, "schema_version": 2}))


def test_v2_current_candidate_is_read(fake: FakeGitHub) -> None:
    base = workflow()
    v2 = {k: v for k, v in base.items() if k not in ("code", "docs")}
    v2.update(schema_version=2, current_candidate={"code": base["code"], "docs": base["docs"]})
    assert errors(validate_workflow(v2)) == []
    assert candidate_report(GitHub(fake.run), v2, require_ready=True).ok
    bad = {**v2, "current_candidate": {"code": {"pr": 1, "sha": "short"}}}
    assert "code.sha" in [p.path for p in errors(validate_workflow(bad))]
