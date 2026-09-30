"""Deterministic workflow operations. Each one either succeeds with its checks recorded, or raises
`CheckFailed` before any dependent action happens."""

from __future__ import annotations

import copy
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .github import REPOS, GitHub, same_text
from .model import NON_ACTIONABLE, candidates, render_body, split_body
from .transitions import check_transition
from .validate import errors, validate_workflow

REVIEW_OR_HANDOFF_STATES = frozenset(
    {
        "CONTRACT_REVIEW",
        "IMPLEMENTATION_REVIEW",
        "FINAL_CONTRACT_REVIEW",
        "CLOSURE_REVIEW",
        "CONTRACT_CONVERGENCE",
    }
)


class CheckFailed(RuntimeError):
    pass


@dataclass
class Report:
    ok: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def check(self, condition: bool, label: str) -> None:
        (self.ok if condition else self.failed).append(label)

    def raise_if_failed(self, verdict: str) -> None:
        if self.failed:
            raise CheckFailed(f"{verdict}: " + "; ".join(self.failed))


def commit_state(
    gh: GitHub,
    repo: str,
    number: int,
    mutate: Callable[[dict[str, Any]], str | None],
    allowed: set[str],
    dry_run: bool = False,
) -> tuple[list[str], str]:
    """The coordination-state commit rule (`agent-workflow.md` §11.1.1), steps 1-7.

    `mutate(workflow)` edits a deep copy of the current workflow object in place and may return
    replacement prose. Returns (changed keys, the new body). Raises before writing when the intended
    state is invalid, changes a key outside `allowed`, or makes an illegal transition; raises after
    writing when the re-fetched remote state is not semantically equal to the intended one."""
    current = split_body(gh.issue(repo, number)["body"])
    old = current.workflow
    new_workflow = copy.deepcopy(old)
    prose = mutate(new_workflow)
    changed = sorted(k for k in set(old) | set(new_workflow) if old.get(k) != new_workflow.get(k))
    outside = [k for k in changed if k not in allowed]
    if outside:
        raise CheckFailed(f"patch changed keys outside ALLOWED: {outside}")
    reason = check_transition(old.get("status", ""), new_workflow.get("status", ""))
    if reason:
        raise CheckFailed(reason)
    state = dict(current.state)
    state["workflow"] = new_workflow
    body = render_body(state, prose if prose is not None else current.prose)
    blocking = errors(validate_workflow(new_workflow, len(body)))
    if blocking:
        raise CheckFailed("intended state invalid: " + "; ".join(map(str, blocking)))
    if dry_run:
        return changed, body
    gh.edit_issue_body(repo, number, body)
    remote = gh.issue(repo, number)["body"]
    parsed = split_body(remote)
    remote_errors = errors(validate_workflow(parsed.workflow, len(remote)))
    if remote_errors:
        raise CheckFailed("FAILED STATE COMMIT: remote state invalid: " + "; ".join(map(str, remote_errors)))
    if parsed.state != state:
        raise CheckFailed("FAILED STATE COMMIT: re-fetched state is not semantically equal (§11.1.1)")
    if not same_text(remote, body):
        raise CheckFailed("FAILED STATE COMMIT: re-fetched body differs from the written body")
    return changed, body


def candidate_report(gh: GitHub, workflow: dict[str, Any], require_ready: bool) -> Report:
    """Exact-SHA candidate checks for `code`/`docs` (§5, §11.3)."""
    report = Report()
    for side, candidate in candidates(workflow).items():
        if not isinstance(candidate, dict) or candidate.get("sha") is None:
            continue
        repo, sha = REPOS[side], candidate["sha"]
        report.check(gh.commit_exists(repo, sha), f"{side} {sha[:12]} remote-reachable")
        pr_number = candidate.get("pr")
        if isinstance(pr_number, int) and candidate.get("merged_sha") is None:
            pr = gh.pr(repo, pr_number)
            report.check(pr["state"] == "OPEN", f"{side} PR #{pr_number} open")
            report.check(pr["headRefOid"] == sha, f"{side} PR #{pr_number} head == {sha[:12]}")
            if require_ready:
                report.check(not pr["isDraft"], f"{side} PR #{pr_number} ready for review")
    return report


def handoff_report(gh: GitHub, repo: str, number: int) -> Report:
    """Handoff validation (`agent-workflow.md` §11.11)."""
    issue = gh.issue(repo, number)
    body = split_body(issue["body"])
    workflow = body.workflow
    report = Report()
    report.check(issue["state"] == "OPEN", "coordination issue OPEN")
    status = workflow.get("status")
    report.check(
        status not in NON_ACTIONABLE | {"BLOCKED_FOR_OWNER"},
        f"status {status} permits a handoff",
    )
    report.check(not errors(validate_workflow(workflow)), "state block valid")
    report.check(bool(workflow.get("next_owner")), "NEXT_OWNER present")
    report.check(bool(workflow.get("next_action")), "NEXT_ACTION present")
    quarantine = workflow.get("quarantine") or {}
    report.check(
        not (isinstance(quarantine, dict) and quarantine.get("derived_from_quarantined_artifact")),
        "candidate not derived from a quarantined artifact",
    )
    candidates = candidate_report(gh, workflow, require_ready=status in REVIEW_OR_HANDOFF_STATES)
    report.ok += candidates.ok
    report.failed += candidates.failed
    return report


def guarded_merge(
    gh: GitHub, repo: str, number: int, sha: str, wait: Callable[[float], None] = time.sleep
) -> str:
    """Exact-head squash merge plus post-merge containment (§11.3, §11.6, §12). Returns the merge SHA."""
    pr = gh.pr(repo, number)
    for _ in range(5):
        if pr["mergeable"] != "UNKNOWN":
            break
        wait(3)
        pr = gh.pr(repo, number)
    report = Report()
    report.check(pr["state"] == "OPEN", f"PR #{number} open")
    report.check(not pr["isDraft"], f"PR #{number} not draft")
    report.check(pr["headRefOid"] == sha, f"PR #{number} head == approved {sha[:12]} (else STOP)")
    report.check(pr["mergeable"] == "MERGEABLE", f"PR #{number} mergeable")
    report.raise_if_failed("MERGE BLOCKED")
    gh.merge_squash(repo, number, sha)
    post = gh.pr(repo, number)
    if post["state"] != "MERGED" or not post.get("mergeCommit"):
        raise CheckFailed(f"PR #{number} did not merge")
    merge_sha: str = post["mergeCommit"]["oid"]
    branch = gh.default_branch(repo)
    if not gh.contains(repo, branch, merge_sha):
        raise CheckFailed(f"merge {merge_sha[:12]} not reachable from {branch}")
    return merge_sha


def verified_comment(gh: GitHub, repo: str, number: int, body: str, kind: str = "issue") -> str:
    """Post, re-fetch and byte-compare a comment (a history record must survive transport intact)."""
    url = gh.comment(repo, number, body, kind)
    comment_id = url.rsplit("issuecomment-", 1)[-1]
    if not same_text(gh.comment_body(repo, comment_id), body):
        raise CheckFailed(f"comment {url} differs from the posted text")
    return url
