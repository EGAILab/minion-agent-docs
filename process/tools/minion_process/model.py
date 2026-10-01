"""Coordination-state model: the canonical vocabulary of `process/coordination-state.md` and the
issue-body container (one fenced YAML block, then free prose)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml  # type: ignore[import-untyped]

STATUSES = (
    "SCOPING",
    "CONTRACT_DRAFT",
    "CONTRACT_REVIEW",
    "PYTHON_IMPLEMENTATION",
    "IMPLEMENTATION_REVIEW",
    "REMEDIATION",
    "CONTRACT_CONVERGENCE",
    "FINAL_CONTRACT_REVIEW",
    "RUST_IMPLEMENTATION",
    "CLOSURE_REVIEW",
    "WAITING_FOR_TRIGGER",
    "CLOSED",
    "INCIDENT",
    "INVALID_UNAUTHORIZED",
    "BLOCKED_FOR_OWNER",
)
"""`coordination-state.md` §3.1."""

ACTIVE = frozenset(
    {
        "SCOPING",
        "CONTRACT_DRAFT",
        "CONTRACT_REVIEW",
        "PYTHON_IMPLEMENTATION",
        "IMPLEMENTATION_REVIEW",
        "REMEDIATION",
        "CONTRACT_CONVERGENCE",
        "FINAL_CONTRACT_REVIEW",
        "RUST_IMPLEMENTATION",
        "CLOSURE_REVIEW",
        "BLOCKED_FOR_OWNER",
    }
)
"""`coordination-state.md` §4.1: states requiring `next_owner` and `next_action`."""

NON_ACTIONABLE = frozenset({"INCIDENT", "INVALID_UNAUTHORIZED"})
OWNERS = frozenset({"Claude", "Codex", "Owner"})

FENCE_OPEN = "```yaml\n"
FENCE_CLOSE = "\n```"


class BodyFormatError(ValueError):
    """The issue body does not start with the canonical fenced-YAML state block."""


@dataclass(frozen=True)
class IssueBody:
    """An issue body split into its canonical state object and the prose that follows it."""

    state: dict[str, Any]
    prose: str

    @property
    def workflow(self) -> dict[str, Any]:
        workflow = self.state.get("workflow")
        if not isinstance(workflow, dict):
            raise BodyFormatError("state block has no `workflow` mapping")
        return workflow


def normalize(text: str) -> str:
    """One multiline document: strip a BOM, and use LF line endings (`agent-workflow.md` §11.1.1)."""
    return text.lstrip("\ufeff").replace("\r\n", "\n")


def split_body(body: str) -> IssueBody:
    """Parse `body`: it must start with the fenced YAML block (`coordination-state.md` §2)."""
    text = normalize(body)
    if not text.startswith(FENCE_OPEN):
        raise BodyFormatError("issue body does not start with a ```yaml state block")
    end = text.find(FENCE_CLOSE, len(FENCE_OPEN))
    if end < 0:
        raise BodyFormatError("unterminated ```yaml state block")
    state = yaml.safe_load(text[len(FENCE_OPEN) : end])
    if not isinstance(state, dict):
        raise BodyFormatError("state block is not a YAML mapping")
    rest = text[end + len(FENCE_CLOSE) :]
    return IssueBody(state=state, prose=rest[1:] if rest.startswith("\n") else rest)


def render_body(state: dict[str, Any], prose: str) -> str:
    """The canonical body for `state` followed by `prose` (the inverse of `split_body`)."""
    text: str = yaml.safe_dump(state, sort_keys=False, width=110, allow_unicode=True)
    return FENCE_OPEN + text + "```\n" + prose


def candidates(workflow: dict[str, Any]) -> dict[str, Any]:
    """The `code`/`docs` candidate entries: the single accessor every consumer uses (CE-PROC-L13-01
    rule 8), read only after validation. A supplied v2 `current_candidate` is never rerouted to the
    v1 top-level form, even when malformed (rule 2)."""
    if "current_candidate" in workflow:
        current = workflow["current_candidate"]
        source = current if isinstance(current, dict) else {}
    else:
        source = workflow
    return {side: source.get(side) for side in ("code", "docs")}
