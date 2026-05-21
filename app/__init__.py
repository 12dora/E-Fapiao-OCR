import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_PACKAGE_NAME = "e-fapiao-ocr"


def _source_tree_version() -> str | None:
    for parent in Path(__file__).resolve().parents:
        pyproject = parent / "pyproject.toml"
        if not pyproject.is_file():
            continue
        try:
            project = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {})
        except (OSError, tomllib.TOMLDecodeError):
            return None
        if project.get("name") == _PACKAGE_NAME and isinstance(project.get("version"), str):
            return project["version"]
    return None


try:
    __version__ = _source_tree_version() or version(_PACKAGE_NAME)
except PackageNotFoundError:
    __version__ = "0.0.0"
