from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt

from backend.app.domain.shared.exceptions.domain_exception import DomainException


class JWTHandler:
    """
    Creates and decodes JWT access tokens.

    Token payload:
        sub     → user_id
        tid     → tenant_id
        role    → user role string
        exp     → expiry timestamp
        iat     → issued-at timestamp
        jti     → unique token id (for future revocation)
    """

    def __init__(self, secret_key: str, algorithm: str, expiry_minutes: int) -> None:
        self._secret = secret_key
        self._algorithm = algorithm
        self._expiry_minutes = expiry_minutes

    def create_access_token(
        self,
        user_id: str,
        tenant_id: str,
        role: str,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload: Dict[str, Any] = {
            "sub": user_id,
            "tid": tenant_id,
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=self._expiry_minutes),
            "jti": str(uuid.uuid4()),
        }
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            return payload
        except JWTError as exc:
            raise DomainException(
                message=f"Invalid or expired token: {exc}",
                code="INVALID_TOKEN",
            ) from exc

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Backward-compatible alias used by the websocket auth path."""
        return self.decode_token(token)

    def get_user_id(self, token: str) -> str:
        return self.decode_token(token)["sub"]

    def get_tenant_id(self, token: str) -> str:
        return self.decode_token(token)["tid"]

    def get_role(self, token: str) -> str:
        return self.decode_token(token)["role"]
