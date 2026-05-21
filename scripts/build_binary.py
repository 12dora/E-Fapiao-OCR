"""Build a standalone efapiao binary for the current platform."""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def main() -> int:
    args = _parse_args()
    version = args.version.lstrip("v")
    target = args.target or _default_target()
    binary_name = "efapiao.exe" if target.startswith("windows-") else "efapiao"
    work_name = f"efapiao-{version}-{target}"
    dist_dir = DIST / work_name
    archive_base = DIST / work_name

    _ensure_pyinstaller()
    shutil.rmtree(dist_dir, ignore_errors=True)
    (BUILD / "pyinstaller").mkdir(parents=True, exist_ok=True)
    DIST.mkdir(exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "efapiao",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(BUILD / "pyinstaller"),
        "--specpath",
        str(BUILD / "pyinstaller"),
        str(ROOT / "app" / "cli.py"),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)

    binary = dist_dir / binary_name
    if not binary.is_file():
        generated = dist_dir / "efapiao"
        if generated.is_file() and binary != generated:
            generated.rename(binary)
    if not binary.is_file():
        raise SystemExit(f"binary not found: {binary}")

    _write_release_files(dist_dir, version, target)
    archive = _make_archive(dist_dir, archive_base, windows=target.startswith("windows-"))
    print(archive)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build standalone efapiao binary")
    parser.add_argument(
        "--version",
        required=True,
        help="SemVer version, with or without leading v",
    )
    parser.add_argument(
        "--target",
        default="",
        help="Artifact target name, e.g. linux-x86_64, darwin-arm64, windows-x86_64",
    )
    return parser.parse_args()


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError as e:
        raise SystemExit('PyInstaller 未安装，请先运行: pip install -e ".[build-bin]"') from e


def _default_target() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    system_map = {
        "darwin": "darwin",
        "linux": "linux",
        "windows": "windows",
    }
    machine_map = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    return f"{system_map.get(system, system)}-{machine_map.get(machine, machine)}"


def _write_release_files(dist_dir: Path, version: str, target: str) -> None:
    (dist_dir / "README.txt").write_text(
        "\n".join(
            [
                "E-Fapiao-OCR standalone binary",
                f"Version: {version}",
                f"Target: {target}",
                "",
                "Usage:",
                "  efapiao --version",
                "  efapiao parse invoice.pdf --pretty",
                "  efapiao serve --host 127.0.0.1 --port 8000",
                "",
                "Notes:",
                "- Release binaries include the rule engine and optional HTTP/Tencent OCR vendors.",
                "- CnOCR local model support is intentionally not bundled in default release "
                "assets.",
                "- Linux builds require libzbar at runtime for QR decoding.",
            ]
        ),
        encoding="utf-8",
    )


def _make_archive(dist_dir: Path, archive_base: Path, *, windows: bool) -> Path:
    if windows:
        archive = Path(f"{archive_base}.zip")
        if archive.exists():
            archive.unlink()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(dist_dir.iterdir()):
                zf.write(path, arcname=f"{dist_dir.name}/{path.name}")
        return archive

    archive = Path(f"{archive_base}.tar.gz")
    if archive.exists():
        archive.unlink()
    with tarfile.open(archive, "w:gz") as tf:
        for path in sorted(dist_dir.iterdir()):
            tf.add(path, arcname=f"{dist_dir.name}/{path.name}")
    return archive


if __name__ == "__main__":
    raise SystemExit(main())
