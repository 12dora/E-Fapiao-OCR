"""FastAPI 入口。仅负责 app 装配，路由实现见 app.api.routes。"""

from fastapi import FastAPI

from app import __version__
from app.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="E-Fapiao-OCR",
        version=__version__,
        description="数电发票 PDF → 结构化 JSON 解析 API",
    )
    app.include_router(router, prefix="/v1")
    return app


app = create_app()
