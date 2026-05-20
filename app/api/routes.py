"""HTTP 路由层。

实现 DESIGN.md §5 中定义的 5 个端点：
  - POST /invoices/parse
  - POST /invoices/parse-and-forward
  - GET  /health
  - GET  /capabilities

TODO(M1): 实现 /invoices/parse 与 /health
TODO(M2): /capabilities
TODO(M3): /invoices/parse-and-forward + API Key 鉴权
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
