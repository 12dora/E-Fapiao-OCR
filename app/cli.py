"""CLI 入口 —— 给二进制 / 任意语言宿主程序集成用（DESIGN.md §13 形态二）。

用法：
    efapiao parse <file.pdf>                   # 解析单文件，JSON 输出到 stdout
    efapiao parse -                            # 从 stdin 读字节，JSON 到 stdout
    efapiao parse <file> --pretty              # 美化输出
    efapiao serve                              # 启动本地 HTTP 服务（等价于 uvicorn app.main:app）
    efapiao capabilities                       # 输出当前支持的 format / invoice_type

退出码遵循 app.errors 中的映射约定，便于宿主程序判定结果。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app import __version__
from app.config import settings
from app.errors import InvalidInput, ParseFailed, RuleEngineUnhandled, UnsupportedFormat


def _print_error(
    code: str,
    message: str,
    *,
    ocr_mode: str = "auto",
    ocr_required: bool = False,
    ocr_used: bool = False,
    ocr_vendor: str | None = None,
    document_type: str | None = None,
    invoice_type: str | None = None,
) -> None:
    print(
        json.dumps(
            {
                "status": "error",
                "code": code,
                "message": message,
                "document_type": document_type,
                "invoice_type": invoice_type,
                "engine": _engine_status(
                    ocr_mode,
                    ocr_required=ocr_required,
                    ocr_used=ocr_used,
                    ocr_vendor=ocr_vendor,
                ),
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )


def _cmd_parse(args: argparse.Namespace) -> int:
    from app.sdk import parse_invoice

    if args.file == "-":
        content = sys.stdin.buffer.read()
    else:
        path = Path(args.file)
        if not path.is_file():
            print(f"file not found: {args.file}", file=sys.stderr)
            return 2
        content = path.read_bytes()

    try:
        result = parse_invoice(content, hint_type=args.hint, ocr_mode=args.ocr_mode)
    except InvalidInput as e:
        _print_error("invalid_input", str(e), ocr_mode=args.ocr_mode)
        return 2
    except UnsupportedFormat as e:
        _print_error("unsupported_format", str(e), ocr_mode=args.ocr_mode)
        return 3
    except RuleEngineUnhandled as e:
        _print_error(
            "rule_unhandled",
            str(e),
            ocr_mode=args.ocr_mode,
            ocr_required=e.ocr_required,
            ocr_used=e.ocr_used,
            document_type=e.document_type,
            invoice_type=e.invoice_type,
        )
        return 4
    except ParseFailed as e:
        _print_error("parse_failed", str(e), ocr_mode=args.ocr_mode)
        return 4
    except NotImplementedError as e:
        _print_error(
            "not_implemented",
            str(e),
            ocr_mode=args.ocr_mode,
            ocr_required=True,
        )
        return 5

    indent = 2 if args.pretty else None
    print(
        json.dumps(
            {
                "status": "ok",
                "data": result,
                "engine": _engine_status(
                    args.ocr_mode,
                    ocr_used=result.get("source", {}).get("extracted_by") == "ocr",
                    ocr_vendor=result.get("source", {}).get("ocr_vendor"),
                ),
            },
            ensure_ascii=False,
            indent=indent,
        )
    )
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from app.config import settings

    uvicorn.run(
        "app.main:app",
        host=args.host or settings.host,
        port=args.port or settings.port,
        workers=args.workers,
    )
    return 0


def _cmd_capabilities(_: argparse.Namespace) -> int:
    from app.config import settings
    from app.core.capabilities import build_capabilities

    print(json.dumps(build_capabilities(settings), ensure_ascii=False, indent=2))
    return 0


def _engine_status(
    ocr_mode: str,
    *,
    ocr_required: bool = False,
    ocr_used: bool = False,
    ocr_vendor: str | None = None,
) -> dict[str, object]:
    return {
        "rule_engine": "attempted",
        "ocr_mode": ocr_mode,
        "ocr_enabled": settings.image_ocr_enabled,
        "ocr_used": ocr_used,
        "ocr_required": ocr_required,
        "ocr_vendor": ocr_vendor,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="efapiao", description="E-Fapiao-OCR CLI")
    p.add_argument("--version", action="version", version=f"efapiao {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    parse_p = sub.add_parser("parse", help="解析单个发票文件，JSON 输出到 stdout")
    parse_p.add_argument("file", help="发票文件路径，使用 - 从 stdin 读取")
    parse_p.add_argument("--hint", choices=["pdf", "ofd", "image", "auto"], default="auto")
    parse_p.add_argument(
        "--ocr-mode",
        choices=["auto", "disabled", "required"],
        default="auto",
        help=(
            "OCR 使用策略：auto 使用已配置 vendor，disabled 仅用规则引擎，"
            "required 要求可走 OCR 的路径必须启用 OCR"
        ),
    )
    parse_p.add_argument("--pretty", action="store_true", help="美化 JSON 输出")
    parse_p.set_defaults(func=_cmd_parse)

    serve_p = sub.add_parser("serve", help="启动本地 HTTP 服务")
    serve_p.add_argument("--host", default=None)
    serve_p.add_argument("--port", type=int, default=None)
    serve_p.add_argument("--workers", type=int, default=1)
    serve_p.set_defaults(func=_cmd_serve)

    caps_p = sub.add_parser("capabilities", help="输出当前支持的格式与发票类型")
    caps_p.set_defaults(func=_cmd_capabilities)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
