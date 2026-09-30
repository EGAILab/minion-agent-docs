"""Structural validation of a coordination-state `workflow` object (`coordination-state.md` §4-§9,
§13). It enforces workflow structure only; it never decides semantics (`agent-workflow.md` §12.6)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .model import ACTIVE, NON_ACTIONABLE, OWNERS, STATUSES, candidates

SHA = re.compile(r"^[0-9a-f]{40}$")

LEAN_BODY_CHARS = 8000
"""`coordination-state.md` §13: a current-state body above this is a lean-state warning."""

HISTORY_KEYS = ("remediations", "reviews", "review_history", "history_log")
"""Keys that carry history rather than current state (`coordination-state.md` §13)."""


@dataclass(frozen=True)
class Problem:
    level: str  # "error" | "warning"
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.level.upper()}: {self.path}: {self.message}"


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in ("", "none", "null"))


def validate_workflow(workflow: dict[str, Any], body_chars: int | None = None) -> list[Problem]:
    """Every structural problem in `workflow`; errors block a state commit, warnings do not."""
    problems: list[Problem] = []

    def error(path: str, message: str) -> None:
        problems.append(Problem("error", path, message))

    def warn(path: str, message: str) -> None:
        problems.append(Problem("warning", path, message))

    status = workflow.get("status")
    if status not in STATUSES:
        error("status", f"unknown status {status!r} (allowed: {', '.join(STATUSES)})")
        return problems

    owner, action = workflow.get("next_owner"), workflow.get("next_action")
    if status in ACTIVE:
        if _missing(owner):
            error("next_owner", f"active status {status} requires next_owner")
        elif owner not in OWNERS:
            error("next_owner", f"unknown owner {owner!r} (allowed: {', '.join(sorted(OWNERS))})")
        if _missing(action):
            error("next_action", f"active status {status} requires next_action")
    if status == "BLOCKED_FOR_OWNER" and owner != "Owner":
        error("next_owner", "BLOCKED_FOR_OWNER requires next_owner: Owner")
    if status == "WAITING_FOR_TRIGGER":
        if _missing(workflow.get("deferred_trigger")):
            error("deferred_trigger", "WAITING_FOR_TRIGGER requires deferred_trigger")
        if not _missing(owner) or not _missing(action):
            error("next_owner", "WAITING_FOR_TRIGGER requires next_owner/next_action null")

    for side, candidate in candidates(workflow).items():
        if candidate is None:
            continue
        if not isinstance(candidate, dict):
            error(side, "must be a mapping")
            continue
        sha = candidate.get("sha")
        if sha is not None and not (isinstance(sha, str) and SHA.match(sha)):
            error(f"{side}.sha", f"not a full 40-hex SHA: {sha!r}")
        pr = candidate.get("pr")
        if pr is not None and not isinstance(pr, int):
            error(f"{side}.pr", f"PR must be an integer, got {pr!r}")

    convergence = workflow.get("convergence")
    if status == "CONTRACT_CONVERGENCE" and (
        not isinstance(convergence, dict) or _missing(convergence.get("episode"))
    ):
        error("convergence.episode", "CONTRACT_CONVERGENCE requires convergence.episode")
    if isinstance(convergence, dict):
        open_findings = convergence.get("open_findings", [])
        if not isinstance(open_findings, list):
            error("convergence.open_findings", "must be a list")
        elif status == "FINAL_CONTRACT_REVIEW" and open_findings:
            error(
                "convergence.open_findings",
                "FINAL_CONTRACT_REVIEW with open convergence findings: " + ", ".join(open_findings),
            )
        checkpoint = convergence.get("checkpoint")
        if checkpoint is not None and not isinstance(checkpoint, str):
            error("convergence.checkpoint", "must be a string")

    lean = workflow.get("schema_version", 1) >= 2
    for key in ("requirements", "open_findings", "provisionally_closed"):
        value = workflow.get(key)
        if value is None or isinstance(value, list):
            continue  # container shape first (agent-workflow.md §8)
        if isinstance(value, dict) and key != "requirements" and not lean:
            warn(key, "legacy v1 mapping form; schema v2 uses a list of finding IDs (details in assurance)")
        else:
            error(key, "must be a list")

    quarantine = workflow.get("quarantine")
    if (
        isinstance(quarantine, dict)
        and quarantine.get("derived_from_quarantined_artifact")
        and status not in NON_ACTIONABLE
    ):
        error("quarantine", "candidate derived from a quarantined artifact (§11.12)")

    governance = workflow.get("governance_source")
    if governance is not None and not isinstance(governance, (dict, str)):
        error("governance_source", "must be a mapping or a link (§11.10)")

    for key in HISTORY_KEYS:
        if key in workflow or any(isinstance(v, dict) and key in v for v in workflow.values()):
            warn(key, "history belongs in assurance/comments; reference it via history.assurance_index")
    if body_chars is not None and body_chars > LEAN_BODY_CHARS:
        warn("body", f"{body_chars} characters exceeds the lean current-state budget {LEAN_BODY_CHARS}")
    return problems


def errors(problems: list[Problem]) -> list[Problem]:
    return [p for p in problems if p.level == "error"]
