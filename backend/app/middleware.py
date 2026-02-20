"""
Middleware for authentication, rate limiting, and request tracing.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("middleware")
settings = get_settings()

# ── In-memory rate limit store (use Redis in production) ──────────
_rate_store: dict[str, list[float]] = {}


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Inject a unique request ID and log request/response cycle."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.perf_counter()
        logger.info(
            "REQ %s | %s %s | client=%s",
            request_id,
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown",
        )

        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "RES %s | %s %s | status=%d | %.1fms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        response.headers["X-Request-ID"] = request_id
        return response


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Validate X-API-Key header on /api/* routes.
    Skips health, docs, and openapi endpoints.
    """

    SKIP_PATHS = {"/", "/health", "/api/health", "/docs", "/redoc", "/openapi.json"}
    SKIP_PREFIXES = ("/api/health", "/api/sessions", "/docs", "/redoc")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip non-API routes and OPTIONS (CORS preflight)
        path = request.url.path.rstrip("/")
        if (
            request.method == "OPTIONS"
            or path in self.SKIP_PATHS
            or path.startswith(self.SKIP_PREFIXES)
            or not path.startswith("/api")
        ):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key", "")
        if api_key != settings.api_key:
            logger.warning("Unauthorized request to %s", path)
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window rate limiter (in-memory for demo)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "0.0.0.0"
        now = time.time()
        window = 60.0  # 1 minute

        # Clean old entries
        timestamps = _rate_store.get(client_ip, [])
        timestamps = [t for t in timestamps if now - t < window]
        _rate_store[client_ip] = timestamps

        if len(timestamps) >= settings.rate_limit_per_minute:
            logger.warning("Rate limit exceeded for %s", client_ip)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )

        timestamps.append(now)
        _rate_store[client_ip] = timestamps
        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    """Register all middleware on the FastAPI app (order matters — last added runs first)."""
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(APIKeyMiddleware)
    app.add_middleware(RequestTracingMiddleware)
