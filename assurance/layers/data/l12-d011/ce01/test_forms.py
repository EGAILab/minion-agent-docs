"""CE-L12D011-01 characterization: how pytest -rA renders each failure form (no writes, no spawns)."""

import importlib
import os

import pytest


def test_assert_bare():
    assert "a" == "b"


def test_assert_message():
    assert "a" == "b", "PREFIX LOST: The fake"


def test_assert_empty_message():
    assert "a" == "b", ""


def test_name_error_marker():
    raise NameError("PREFIX LOST: counterfeit setup failure")


def test_real_name_error():
    PREFIX_LOST_helper()  # noqa: F821


def test_unbound_local():
    if False:
        helper = 1
    helper  # noqa: B018


def test_import_marker():
    importlib.import_module("PREFIX LOST")


def test_native_value_error():
    os.stat("a\0b")


def test_custom_qualified():
    class Boom(Exception):
        pass

    raise Boom("PREFIX LOST")


def test_assertion_error_raised_explicitly():
    raise AssertionError("PREFIX LOST: hand-raised")


def test_assertion_subclass():
    class Sub(AssertionError):
        pass

    raise Sub("PREFIX LOST: subclass")


def test_multiline_message():
    assert False, "LONG NAME CONVERTED: line one\nline two"


def test_raises_no_match():
    with pytest.raises(ValueError, match="x"):
        raise ValueError("y")


def test_pytest_fail():
    pytest.fail("PREFIX LOST: via pytest.fail")


def test_exception_group():
    raise ExceptionGroup("PREFIX LOST group", [NameError("x")])


def test_assert_long_strings():
    got = "The property 'options.cwd' must be a string, Uint8Array, or URL without null bytes. Received 'd\\x00'"
    want = "The property 'options.cwd' must be a string, Uint8Array, or URL without null bytes. Received 'x\\\\d\\x00'"
    assert got == want


@pytest.fixture
def broken():
    raise NameError("PREFIX LOST: in fixture")


def test_fixture_error(broken):
    pass
