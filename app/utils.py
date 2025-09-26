from datetime import datetime

from starlette.datastructures import URL
from starlette.requests import Request


def datetime_to_str(value: datetime) -> str:
    """
    :param value: `datetime.datetime` value
    :return: ``ISO 8601`` date with ``Z`` format
    """
    return value.isoformat().replace("+00:00", "Z")


def get_proxy_aware_url(request: Request) -> URL:
    """
    Constructs a URL from the request, handling proxy forwarding headers.

    When behind a proxy, uses x-forwarded-* headers to reconstruct the original URL
    with the correct scheme, host, port, and path prefix.

    :param request: The FastAPI/Starlette request object
    :return: URL object with proxy-aware scheme, host, port, and path
    """
    prefix = request.headers.get("x-forwarded-prefix", "").rstrip("/")
    if prefix:
        host = request.headers.get("x-forwarded-host", request.url.hostname)
        protocol = request.headers.get("x-forwarded-proto", request.url.scheme)
        port = request.headers.get("x-forwarded-port", request.url.port)
        return request.url.replace(
            scheme=protocol,
            hostname=host,
            port=port,
            path=prefix + request.url.path,
        )
    return request.url
