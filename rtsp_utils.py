from urllib.parse import quote, urlsplit, urlunsplit


def add_credentials_to_rtsp_url(url: str, username: str, password: str) -> str:
    parts = urlsplit(url)
    if parts.scheme.lower() != "rtsp":
        return url
    if "@" in parts.netloc:
        return url
    host = parts.hostname or ""
    if not host:
        return url
    port = f":{parts.port}" if parts.port else ""
    user = quote(username, safe="")
    pwd = quote(password, safe="")
    netloc = f"{user}:{pwd}@{host}{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def build_rtsp_url(ip: str, path: str, username: str = "", password: str = "", port: int = 554) -> str:
    clean_path = path if path.startswith("/") else f"/{path}"
    base = f"rtsp://{ip}:{port}{clean_path}"
    if username:
        return add_credentials_to_rtsp_url(base, username, password)
    return base
