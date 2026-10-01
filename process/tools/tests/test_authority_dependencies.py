"""The pinned external authority dependency rule (`process/authority-dependencies.md`): every active
authority runner acquires npm dependencies ONLY through the canonical `acquire_npm_pinned.sh`, whose
per-evidence copies are byte-identical, so offline and network acquisition share one verification
path. The helper's own negative controls are `process/tools/authority/selftest.sh`."""

from __future__ import annotations

from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[3]
CANONICAL = DOCS / "process" / "tools" / "authority" / "acquire_npm_pinned.sh"
DATA = DOCS / "assurance" / "layers" / "data"
ACTIVE_RUNNERS = [
    DATA / "l0506-d001" / "harness" / "run_authority.sh",
    DATA / "l0506-d002" / "harness" / "run_authority.sh",
    DATA / "l0206-raw-boundaries" / "harness" / "run.sh",
    DATA / "13-wp132-evidence" / "harness" / "run_authority.sh",
    DATA / "l0506-d003-characterization" / "harness" / "run.sh",
]


@pytest.mark.parametrize("runner", ACTIVE_RUNNERS, ids=lambda p: p.parent.parent.name)
def test_an_active_runner_acquires_only_through_the_canonical_helper(runner: Path) -> None:
    source = runner.read_text(encoding="utf-8")
    code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
    assert '. "$H/acquire_npm_pinned.sh"' in code
    assert "acquire_npm_pinned " in code
    assert "npm pack" not in code  # no side door around the shared verification
    # PROC-AUTHDEP-R001: the pin is read from the verified pinned COMMIT, never the working tree
    assert 'show "' in code and ':package-lock.json" > "$S/pinned-package-lock.json"' in code
    assert '"$S/pinned-package-lock.json"' in code.split("acquire_npm_pinned ", 2)[-1]
    assert '"$PI/package-lock.json"' not in code
    copy = runner.parent / "acquire_npm_pinned.sh"
    assert copy.read_bytes() == CANONICAL.read_bytes(), f"{copy} differs from the canonical helper"


def test_the_helper_reads_its_pin_from_the_lockfile_and_verifies_before_unpacking() -> None:
    helper = CANONICAL.read_text(encoding="utf-8")
    verify = helper.index('[ "$_got" = "$_sri" ]')
    assert helper.index('"node_modules/" + process.argv[2]') < verify  # the pin comes from the lockfile
    assert verify < helper.index("tar -xzf")  # bytes are verified before anything is unpacked
    assert helper.index("tar -xzf") < helper.index("unpacked $_name declares version")
