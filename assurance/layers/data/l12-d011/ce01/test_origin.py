"""Paired observations for C001 (failure origin) and C002 (rendering versus identity)."""

import asyncio
import sys
from pathlib import Path

import pytest

SRC = Path("E:/AI/Projects/OpenMinds/Minions/Minion-Agent/review-worktrees/claude-d011-py/minion-agent-python/src")
sys.path.insert(0, str(SRC))
from minion_agent.execution import subprocess as seam  # noqa: E402

CWD = str(SRC)


def test_genuine_assertion():
    assert "a" == "b", "PREFIX LOST: The fake"


def test_fake_assertion_class():
    fake = type("AssertionError", (Exception,), {"__module__": "builtins"})
    raise fake("PREFIX LOST: The fake")


def test_assert_named_class():
    fake = type("assert ['A', 'Z']", (Exception,), {"__module__": "builtins"})
    raise fake("setup helper failed")


def _helper():
    raise ValueError("embedded null character")


def test_helper_value_error():
    _helper()


def test_genuine_native_through_seam(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(seam, "spawn_rejection", lambda *a, **k: None)  # the mutant: no pre-spawn check
    asyncio.run(seam.LocalSubprocess(CWD).spawn(["python"], seam.SpawnOptions(cwd="d\0")))


def test_native_without_seam():
    asyncio.run(asyncio.create_subprocess_exec("python", "a\0"))
