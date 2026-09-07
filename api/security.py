"""
Security configuration and middleware for Medical Risk XAI API.
Implements rate limiting, CORS hardening, and security headers.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# ---------------------------------------------------------------------------
# Rate Limiting Middleware
# ---------------------------------------------------------------------------

class RateLimiter:
    """In-memory rate limiter for API endpoints."""

    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            "auth": (5, 60),      # 5 requests per minute for auth endpoints
            "api": (100, 60),     # 100 requests per minute for regular API
            "public": (30, 60),   # 30 requests per minute for public endpoints
        }

    def is_allowed(self, key: str, limit_type: str = "api") -> bool:
        """Check if request is within rate limit."""
        now = time.time()
        max_requests, window = self.limits.get(limit_type, (100, 60))

        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < window
        ]

        # Check limit
        if len(self.requests[key]) >= max_requests:
            return False

        self.requests[key].append(now)
        return True

    def get_client_key(self, request: Request) -> str:
        """Generate client key from request."""
        # Use combination of IP and user agent for better tracking
        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = forwarded.split(",")[0] if forwarded else request.client.host
        user_agent = request.headers.get("User-Agent", "unknown")
        return f"{client_ip}:{hash(user_agent)}"


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting to all requests."""

    async def dispatch(self, request: Request, call_next: Callable):
        # Determine limit type based on path
        path = request.url.path

        if path.startswith("/auth/"):
            limit_type = "auth"
        elif path in ["/health", "/auth/demo-accounts"]:
            limit_type = "public"
        else:
            limit_type = "api"

        client_key = rate_limiter.get_client_key(request)

        if not rate_limiter.is_allowed(client_key, limit_type):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please try again later."}
            )

        response = await call_next(request)
        return response


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"

        return response


# ---------------------------------------------------------------------------
# Request Sanitization
# ---------------------------------------------------------------------------

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input to prevent injection attacks."""
    if not isinstance(value, str):
        return str(value)

    # Remove null bytes
    value = value.replace("\x00", "")

    # Limit length
    value = value[:max_length]

    # Remove control characters except newline and tab
    value = "".join(char for char in value if char.isprintable() or char in "\n\t")

    return value.strip()


def sanitize_email(email: str) -> str:
    """Sanitize and validate email format."""
    email = sanitize_string(email, max_length=254).lower()

    # Basic email validation
    if "@" not in email or "." not in email.split("@")[1]:
        raise ValueError("Invalid email format")

    return email


# ---------------------------------------------------------------------------
# Audit Logging Helper
# ---------------------------------------------------------------------------

def create_audit_entry(
    db,
    actor_id: int,
    actor_role: str,
    action: str,
    target_type: str = None,
    target_id: int = None,
    details: dict = None,
    sensitive: bool = False
):
    """Create audit log entry with PII filtering."""
    from api.database import AuditLog
    import json

    # Filter sensitive data from details
    if details and sensitive:
        filtered_details = {
            k: "***REDACTED***" if k in ["password", "hashed_password", "token", "ssn", "dob"] else v
            for k, v in details.items()
        }
    else:
        filtered_details = details

    audit = AuditLog(
        actor_user_id=actor_id,
        actor_role=actor_role,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=json.dumps(filtered_details) if filtered_details else None,
    )
    db.add(audit)
    return audit
