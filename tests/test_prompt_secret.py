"""Tests for masked secret prompts."""

from __future__ import annotations

import io

import pytest

from aurey_wallet_mcp.prompts import read_masked_line


def test_read_masked_line_builds_string_and_echoes() -> None:
    stream = io.StringIO()
    keys = iter(["a", "b", "c", "\n"])

    def read_char() -> str | None:
        try:
            return next(keys)
        except StopIteration:
            return None

    assert read_masked_line(echo="*", read_char=read_char, out=stream) == "abc"
    assert stream.getvalue() == "***\n"


def test_read_masked_line_backspace() -> None:
    stream = io.StringIO()
    keys = iter(["a", "b", "\x7f", "c", "\n"])

    def read_char() -> str | None:
        return next(keys)

    assert read_masked_line(echo="*", read_char=read_char, out=stream) == "ac"
    assert stream.getvalue() == "**\b \b*\n"


def test_read_masked_line_empty_submit() -> None:
    stream = io.StringIO()
    keys = iter(["\n"])

    def read_char() -> str | None:
        return next(keys)

    assert read_masked_line(echo="*", read_char=read_char, out=stream) == ""


def test_read_masked_line_ctrl_c() -> None:
    stream = io.StringIO()
    keys = iter(["a", "\x03"])

    def read_char() -> str | None:
        return next(keys)

    with pytest.raises(KeyboardInterrupt):
        read_masked_line(echo="*", read_char=read_char, out=stream)
