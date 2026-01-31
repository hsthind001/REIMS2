"""
E6-S3: Rate limit key by org/user when available, else by IP.

Provides key_func for SlowAPI to scope rate limits per organization
or per token (user) instead of per IP only.
"""
from slowapi.util import get_remote_address


def get_rate_limit_key(request) -> str:
    """
    Rate limit key: prefer org_id or bearer token, else IP.
    - X-Organization-ID present -> org:{org_id} (org-scoped)
    - Authorization: Bearer present -> bearer:{token_prefix} (user-scoped via token)
    - Else -> IP address
    """
    org_id = request.headers.get("X-Organization-ID") or request.headers.get("x-organization-id")
    if org_id and str(org_id).isdigit():
        return f"org:{org_id}"

    auth = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            # Use first 32 chars of token as key (stable per user session)
            return f"bearer:{token[:32]}"

    return get_remote_address(request)
