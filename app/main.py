"""FastAPI 入口。仅负责 app 装配，路由实现见 app.api.routes。"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import router
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="E-Fapiao-OCR",
        version=__version__,
        description="数电发票 PDF → 结构化 JSON 解析 API",
    )

    @app.middleware("http")
    async def limit_request_body(request: Request, call_next):  # type: ignore[no-untyped-def]
        # 在解析 multipart 之前，凭 Content-Length 直接拒绝超大请求，
        # 避免超大上传在被单文件上限拦下之前就把内存/磁盘顶爆。
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                declared = -1
            if declared > settings.max_request_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "status": "error",
                        "code": "invalid_input",
                        "message": f"请求体超过上限 {settings.max_request_bytes} 字节",
                    },
                )
        return await call_next(request)

    app.include_router(router, prefix="/v1")
    return app


app = create_app()
