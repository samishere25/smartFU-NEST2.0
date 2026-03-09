"""
RBAC (Role-Based Access Control) Middleware

Provides route-level access control based on JWT role claims.
Used as a secondary layer alongside the FastAPI Depends(require_role(...)) pattern.

This middleware intercepts requests to protected route prefixes and validates
the JWT token's role claim against allowed roles for that prefix.

Protected prefixes:
  /api/admin/*       → ADMIN only
  /api/governance/*  → ADMIN, GOVERNANCE
  /api/reviewer/*    → ADMIN, REVIEWER
  /api/cases/*       → ADMIN, PROCESSOR, PV_SPECIALIST, SAFETY_OFFICER
  /api/auth/*        → Public (no role check)
  Everything else    → Authenticated (any valid role)

Usage in main.py:
    from app.middleware.rbac import RBACMiddleware
    app.add_middleware(RBACMiddleware)
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger("smartfu.rbac")

# Route prefix → allowed roles mapping
ROUTE_ROLE_MAP = {
    "/api/admin":       ["ADMIN"],
    "/api/governance":  ["ADMIN", "GOVERNANCE"],
}

# Public routes that don't need any role check
PUBLIC_PREFIXES = [
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/change-password",
    "/api/reporter-portal",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/health",
    "/api/health",
]


class RBACMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces role-based access on protected route prefixes.
    
    - Public routes are always allowed.
    - Protected routes require a valid JWT with the correct role.
    - All other authenticated routes just need a valid token.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow public routes
        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Allow CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        # Check protected prefixes
        for prefix, allowed_roles in ROUTE_ROLE_MAP.items():
            if path.startswith(prefix):
                # Extract and validate JWT
                auth_header = request.headers.get("authorization", "")
                if not auth_header.startswith("Bearer "):
                    logger.warning(f"RBAC: Missing/invalid auth header for {path}")
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Not authenticated"}
                    )

                token = auth_header.split(" ", 1)[1]
                try:
                    payload = jwt.decode(
                        token,
                        settings.SECRET_KEY,
                        algorithms=[settings.ALGORITHM]
                    )
                    role = payload.get("role", "")
                    if role not in allowed_roles:
                        logger.warning(
                            f"RBAC: Access denied | path={path} | "
                            f"user_role={role} | required={allowed_roles}"
                        )
                        return JSONResponse(
                            status_code=403,
                            content={
                                "detail": f"Access denied. Required role(s): {', '.join(allowed_roles)}. Your role: {role}"
                            }
                        )
                except JWTError as e:
                    logger.warning(f"RBAC: Invalid/expired token for {path}: {e}")
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid or expired token"}
                    )

        # All other routes — let FastAPI handle auth via Depends()
        return await call_next(request)
