from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from centri.config import Settings
from centri.feedback.shadow_log import ShadowLogger
from centri.gateway.auth import require_auth


def test_jwt_roles_are_enforced():
    settings = Settings(
        centri_auth_required=True,
        centri_jwt_secret="test-secret-" + ("x" * 32),
        centri_jwt_algorithm="HS256",
    )
    token = jwt.encode(
        {
            "sub": "operator-1",
            "roles": ["operator"],
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.centri_jwt_secret,
        algorithm=settings.centri_jwt_algorithm,
    )

    from fastapi.security import HTTPAuthorizationCredentials

    principal = require_auth(
        settings,
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        {"operator"},
    )
    assert principal.subject == "operator-1"
    with pytest.raises(HTTPException) as error:
        require_auth(
            settings,
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            {"admin"},
        )
    assert error.value.status_code == 403


def test_shadow_logger_redacts_prompt(tmp_path):
    settings = Settings(
        centri_shadow_log_dir=tmp_path,
        centri_redact_telemetry=True,
        centri_auth_required=False,
    )
    logger = ShadowLogger(settings)
    path = logger.log({"prompt": "secret user data", "query": "secret query", "status": "ok"})
    content = path.read_text(encoding="utf-8")
    assert "secret user data" not in content
    assert "prompt_sha256" in content
    assert "query_sha256" in content
