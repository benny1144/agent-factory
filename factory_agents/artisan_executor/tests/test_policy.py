from __future__ import annotations

import pytest

from factory_agents.artisan_executor.core.policy import is_allowed


@pytest.mark.parametrize(
    "cmd,expected",
    [
        ("echo hello", True),
        ("python -V", True),
        ("pytest -q", True),
        ("git status", True),
        ("rm -rf /", False),
        ("powershell Remove-Item -Recurse *", False),
        ("cmd /c del *.*", False),
        (" echo leading space", True),
    ],
)

def test_is_allowed(cmd: str, expected: bool) -> None:
    assert is_allowed(cmd) is expected
