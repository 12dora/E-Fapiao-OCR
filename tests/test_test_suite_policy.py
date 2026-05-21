from __future__ import annotations

from pathlib import Path


def test_tests_do_not_depend_on_local_real_samples() -> None:
    root = Path(__file__).resolve().parent
    offenders = []
    for path in root.glob("test_*.py"):
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8")
        if "docs/sample" in text:
            offenders.append(path.name)

    assert offenders == []
