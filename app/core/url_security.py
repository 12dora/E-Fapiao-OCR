"""URL 安全校验工具。

用于所有向外发起请求的模块，避免 SSRF 与非预期明文 HTTP。
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.errors import InvalidInput


def validate_public_http_url(url: str, *, allow_http: bool = False) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise InvalidInput("URL 必须使用 http 或 https")
    if parsed.scheme == "http" and not allow_http:
        raise InvalidInput("URL 必须使用 https")
    if not parsed.hostname:
        raise InvalidInput("URL 缺少 hostname")
    if _is_blocked_host(parsed.hostname):
        raise InvalidInput("URL 不允许指向本机或内网地址")
    return url


def _is_blocked_host(host: str) -> bool:
    hostname = host.rstrip(".").lower()
    if hostname in {"localhost"} or hostname.endswith(".localhost"):
        return True

    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        addresses = _resolve_host(hostname)

    return any(_is_blocked_ip(address) for address in addresses)


def _resolve_host(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise InvalidInput("URL hostname 无法解析") from e

    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        sockaddr = info[4]
        if sockaddr:
            addresses.append(ipaddress.ip_address(sockaddr[0]))
    if not addresses:
        raise InvalidInput("URL hostname 无法解析")
    return addresses


def _is_blocked_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )
