"""Connector substrate 通用工具。"""

from __future__ import annotations

from ipaddress import ip_address
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"gclid", "fbclid"}
LOCAL_HOSTNAMES = {"localhost", "localhost.localdomain"}


def canonicalize_uri(uri: str) -> str:
    """对 URI 做稳定归一化。"""
    raw = (uri or "").strip()
    if not raw:
        return ""
    if raw.startswith("file://"):
        return raw
    path = Path(raw)
    if path.exists():
        return path.resolve().as_uri()

    parsed = urlparse(raw)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    if scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in TRACKING_QUERY_KEYS and not any(key.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES)
    ]
    normalized_path = parsed.path or "/"
    normalized = parsed._replace(
        scheme=scheme,
        netloc=netloc,
        path=normalized_path,
        query=urlencode(filtered_query),
        fragment="",
    )
    return urlunparse(normalized)


def domain_from_uri(uri: str) -> str:
    """提取 URI 域名。"""
    parsed = urlparse(uri)
    return parsed.netloc.lower()


def fetch_uri_block_reason(uri: str) -> str:
    """返回 fetch URI 的安全拦截原因；空字符串表示允许继续。"""
    parsed = urlparse(uri)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        return "unsupported_scheme"
    host = (parsed.hostname or "").lower()
    if not host:
        return "missing_host"
    if host in LOCAL_HOSTNAMES:
        return "private_or_local_host"
    try:
        address = ip_address(host)
    except ValueError:
        return ""
    if (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_unspecified
        or address.is_reserved
    ):
        return "private_or_local_host"
    return ""
