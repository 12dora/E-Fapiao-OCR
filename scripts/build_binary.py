"""Build a standalone efapiao binary for the current platform."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

from app.ocr_model_profiles import resolve_cnocr_model_profile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build"
MODEL_BUNDLE = BUILD / "model-bundle"
MODEL_CACHE = BUILD / "model-cache"
PYINSTALLER_EXCLUDES = [
    # Development / REPL / formatting helpers.
    "IPython",
    "Pygments",
    "ctags",
    "mypy",
    "pytest",
    "rich",
    "setuptools",
    # Optional networking backends or CLIs not used by the service.
    "h2",
    "httpx._main",
    "python_socks",
    "socksio",
    "trio",
    "uvicorn.workers",
    "watchfiles",
    "websockets",
    "wsproto",
    # Uvicorn standard extras. The binary uses regular asyncio/h11.
    "httptools",
    "uvloop",
    # Optional data/science/display helpers.
    "defusedxml",
    "numpy",
    "pandas",
    "pygame",
    "tabulate",
    # Pillow image formats that are not needed for QR/image OCR input.
    "PIL.AvifImagePlugin",
    "PIL.BlpImagePlugin",
    "PIL.BufrStubImagePlugin",
    "PIL.CurImagePlugin",
    "PIL.DcxImagePlugin",
    "PIL.EpsImagePlugin",
    "PIL.FitsImagePlugin",
    "PIL.FliImagePlugin",
    "PIL.FpxImagePlugin",
    "PIL.GbrImagePlugin",
    "PIL.GribStubImagePlugin",
    "PIL.Hdf5StubImagePlugin",
    "PIL.IcnsImagePlugin",
    "PIL.ImImagePlugin",
    "PIL.ImtImagePlugin",
    "PIL.IptcImagePlugin",
    "PIL.MicImagePlugin",
    "PIL.MpoImagePlugin",
    "PIL.MspImagePlugin",
    "PIL.PalmImagePlugin",
    "PIL.PcdImagePlugin",
    "PIL.PcxImagePlugin",
    "PIL.PdfImagePlugin",
    "PIL.PixarImagePlugin",
    "PIL.PsdImagePlugin",
    "PIL.SgiImagePlugin",
    "PIL.SpiderImagePlugin",
    "PIL.SunImagePlugin",
    "PIL.TgaImagePlugin",
    "PIL.TiffImagePlugin",
    "PIL.WebPImagePlugin",
    "PIL.WmfImagePlugin",
    "PIL.XVThumbImagePlugin",
    "PIL.XbmImagePlugin",
    "PIL.XpmImagePlugin",
]


def main() -> int:
    args = _parse_args()
    version = args.version.lstrip("v")
    target = args.target or _default_target()
    artifact_flavor = args.artifact_flavor or ("with-model" if args.bundle_cnocr_model else "lite")
    binary_name = "efapiao.exe" if target.startswith("windows-") else "efapiao"
    work_name = f"efapiao-{version}-{target}-{artifact_flavor}"
    dist_dir = DIST / work_name
    archive_base = DIST / work_name
    model_data: list[tuple[Path, str]] = []

    _ensure_pyinstaller()
    if args.bundle_cnocr_model:
        _ensure_cnocr()
        model_data = _prepare_cnocr_model_bundle(args.cnocr_model_profile)
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
        "--add-data",
        f"{ROOT / 'pyproject.toml'}{os.pathsep}.",
        "--hidden-import",
        "app.main",
    ]
    for src, dest in model_data:
        cmd.extend(["--add-data", f"{src}{os.pathsep}{dest}"])
    if args.bundle_cnocr_model:
        for module in (
            "cnocr",
            "cnstd",
            "onnxruntime",
            "rapidocr",
            "cv2",
            "numpy",
        ):
            cmd.extend(["--hidden-import", module])
    cnocr_required_modules = {
        "defusedxml",
        "numpy",
        "pandas",
        "rich",
        "setuptools",
        "tabulate",
    }
    for module in PYINSTALLER_EXCLUDES:
        if args.bundle_cnocr_model and module in cnocr_required_modules:
            continue
        cmd.extend(["--exclude-module", module])
    cmd.append(str(ROOT / "app" / "cli.py"))
    subprocess.run(cmd, cwd=ROOT, check=True)

    binary = dist_dir / binary_name
    if not binary.is_file():
        generated = dist_dir / "efapiao"
        if generated.is_file() and binary != generated:
            generated.rename(binary)
    if not binary.is_file():
        raise SystemExit(f"binary not found: {binary}")

    if args.bundle_cnocr_model:
        _copy_external_model_bundle(dist_dir)
    _write_release_files(
        dist_dir,
        version,
        target,
        artifact_flavor=artifact_flavor,
        bundle_cnocr_model=args.bundle_cnocr_model,
        cnocr_model_profile=args.cnocr_model_profile,
    )
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
    parser.add_argument(
        "--artifact-flavor",
        default="",
        help="Artifact suffix flavor, default: lite or with-model",
    )
    parser.add_argument(
        "--bundle-cnocr-model",
        action="store_true",
        help="Bundle CnOCR runtime dependencies and the selected model profile",
    )
    parser.add_argument(
        "--cnocr-model-profile",
        default="invoice-lite",
        help="CnOCR model profile to bundle; default: invoice-lite",
    )
    return parser.parse_args()


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError as e:
        raise SystemExit('PyInstaller 未安装，请先运行: pip install -e ".[build-bin]"') from e


def _ensure_cnocr() -> None:
    try:
        import cnocr  # noqa: F401
    except ImportError as e:
        raise SystemExit('CnOCR 未安装，请先运行: pip install -e ".[ocr-cnocr,build-bin]"') from e


def _prepare_cnocr_model_bundle(profile_name: str) -> list[tuple[Path, str]]:
    profile = resolve_cnocr_model_profile(profile_name)
    from cnocr import CnOcr  # type: ignore[import-not-found]

    rec_root = MODEL_CACHE / "cnocr"
    det_root = MODEL_CACHE / "cnstd"
    CnOcr(
        det_model_name=profile.det_model_name,
        rec_model_name=profile.rec_model_name,
        det_model_backend=profile.det_model_backend,
        rec_model_backend=profile.rec_model_backend,
        rec_root=rec_root,
        det_root=det_root,
    )

    shutil.rmtree(MODEL_BUNDLE, ignore_errors=True)
    rec_src = rec_root / "2.3" / profile.rec_model_name
    det_src = det_root / "1.2" / "ppocr" / profile.det_model_name
    rec_dst = MODEL_BUNDLE / "models" / "cnocr" / "2.3" / profile.rec_model_name
    det_dst = MODEL_BUNDLE / "models" / "cnstd" / "1.2" / "ppocr" / profile.det_model_name
    _copy_model_dir(rec_src, rec_dst)
    _copy_model_dir(det_src, det_dst)
    return [(MODEL_BUNDLE / "models", "models")]


def _copy_model_dir(src: Path, dst: Path) -> None:
    if not src.is_dir():
        raise SystemExit(f"model directory not found: {src}")
    ignore = shutil.ignore_patterns(".cache", "__pycache__", "*.lock")
    shutil.copytree(src, dst, ignore=ignore)


def _copy_external_model_bundle(dist_dir: Path) -> None:
    """Also place models beside the binary for onedir/external inspection."""
    src = MODEL_BUNDLE / "models"
    if src.is_dir():
        shutil.copytree(src, dist_dir / "models", dirs_exist_ok=True)


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


def _write_release_files(
    dist_dir: Path,
    version: str,
    target: str,
    *,
    artifact_flavor: str,
    bundle_cnocr_model: bool,
    cnocr_model_profile: str,
) -> None:
    model_notes = [
        "- Release binaries include the rule engine and optional HTTP/Tencent OCR vendors.",
        "- Linux builds require libzbar at runtime for QR decoding.",
    ]
    if bundle_cnocr_model:
        model_notes.extend(
            [
                "- This asset includes local CnOCR runtime/model files.",
                f"- Bundled CnOCR profile: {cnocr_model_profile}.",
                "- Enable with: EFAPIAO_OCR_VENDOR=cnocr.",
                "- Switch profiles with EFAPIAO_CNOCR_MODEL_PROFILE when the profile is bundled "
                "or can be downloaded at runtime.",
            ]
        )
    else:
        model_notes.extend(
            [
                "- CnOCR local model support is not bundled in this asset.",
                '- Install optional deps separately with: pip install -e ".[ocr-cnocr]".',
            ]
        )

    (dist_dir / "README.txt").write_text(
        "\n".join(
            [
                "E-Fapiao-OCR standalone binary",
                f"Version: {version}",
                f"Target: {target}",
                f"Flavor: {artifact_flavor}",
                "",
                "Usage:",
                "  efapiao --version",
                "  efapiao parse invoice.pdf --pretty",
                "  efapiao serve --host 127.0.0.1 --port 8000",
                "",
                "Notes:",
                *model_notes,
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
