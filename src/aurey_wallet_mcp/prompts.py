"""Terminal secret prompts with visible mask characters."""

from __future__ import annotations

import getpass
import sys
from collections.abc import Callable
from typing import TextIO

ReadCharFn = Callable[[], str | None]


def _read_masked_line(
    *,
    echo: str,
    read_char: ReadCharFn,
    out: TextIO,
) -> str:
    chars: list[str] = []
    while True:
        ch = read_char()
        if ch is None:
            break
        if ch in ("\r", "\n"):
            out.write("\n")
            out.flush()
            break
        if ch in ("\x03",):  # Ctrl+C
            raise KeyboardInterrupt
        if ch in ("\x7f", "\b"):  # backspace
            if chars:
                chars.pop()
                out.write("\b \b")
                out.flush()
            continue
        if ch.isprintable():
            chars.append(ch)
            out.write(echo)
            out.flush()
    return "".join(chars)


def read_masked_line(
    *,
    echo: str = "*",
    read_char: ReadCharFn | None = None,
    out: TextIO | None = None,
) -> str:
    """Read a secret line; print ``echo`` per keystroke when ``read_char`` is provided."""

    if read_char is not None:
        stream = out or sys.stdout
        return _read_masked_line(echo=echo, read_char=read_char, out=stream)

    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            if sys.platform == "win32":
                return _read_masked_windows(echo=echo)
            return _read_masked_unix(echo=echo)
        except (ImportError, OSError, AttributeError):
            pass

    return getpass.getpass("")


def _read_masked_unix(*, echo: str) -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)

        def read_char() -> str | None:
            b = sys.stdin.buffer.read(1)
            if not b:
                return None
            return b.decode("utf-8", errors="replace")

        return _read_masked_line(echo=echo, read_char=read_char, out=sys.stdout)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _read_masked_windows(*, echo: str) -> str:
    import msvcrt

    def read_char() -> str | None:
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            msvcrt.getwch()
            return ""
        return ch

    return _read_masked_line(echo=echo, read_char=read_char, out=sys.stdout)


def prompt_secret(prompt: str, *, echo: str = "*") -> str:
    """Prompt for a secret; show ``echo`` for each typed character on a TTY."""

    sys.stdout.write(prompt)
    sys.stdout.flush()
    try:
        return read_masked_line(echo=echo).strip()
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        sys.stdout.flush()
        raise
