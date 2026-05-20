"""Forwarder —— Webhook 透传。

参考 DESIGN.md §7：
  - fire_and_forget: 后台任务异步 POST，主请求立即返回
  - wait:           等待下游响应，5s 超时，把 status/body 一并回传
  - 禁内网地址（防 SSRF）
  - 强制 HTTPS

TODO: forward(url, payload, headers, mode) -> ForwardResult
"""

from typing import Literal

ForwardMode = Literal["fire_and_forget", "wait"]


async def forward(
    url: str,
    payload: dict,
    headers: dict | None,
    mode: ForwardMode,
) -> dict:
    raise NotImplementedError
