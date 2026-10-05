from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from centri.config import Settings, get_settings


bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]
    claims: dict[str, Any]


def require_auth(
    settings: Settings,
    credentials: HTTPAuthorizationCredentials | None,
    required_roles: set[str] | None = None,
) -> Principal:
    if not settings.centri_auth_required:
        return Principal(subject="local-development", roles=frozenset({"admin"}), claims={})
    if not settings.centri_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT authentication is enabled but CENTRI_JWT_SECRET is not configured",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.centri_jwt_secret,
            algorithms=[settings.centri_jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = str(claims.get("sub", ""))
    roles_claim = claims.get("roles", claims.get("scope", []))
    if isinstance(roles_claim, str):
        roles = frozenset(roles_claim.split())
    elif isinstance(roles_claim, list):
        roles = frozenset(str(role) for role in roles_claim)
    else:
        roles = frozenset()
    if required_roles and not roles.intersection(required_roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return Principal(subject=subject, roles=roles, claims=claims)


def current_principal(
    settings: Settings,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    return require_auth(settings, credentials)


def authenticated_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    return current_principal(get_settings(), credentials)


def admin_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    return principal_with_roles(get_settings(), credentials, {"admin", "operator"})


def principal_with_roles(
    settings: Settings,
    credentials: HTTPAuthorizationCredentials | None,
    roles: set[str],
) -> Principal:
    return require_auth(settings, credentials, required_roles=roles)
