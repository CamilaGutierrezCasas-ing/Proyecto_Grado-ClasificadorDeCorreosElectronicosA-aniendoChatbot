from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
import secrets

import httpx
from jose import jwt
from sqlalchemy.orm import Session
import httpx
from typing import Any


from app.core.config import get_settings
from app.core.security import decode_token
from app.models.linked_account import LinkedAccount
from app.models.user import User

settings = get_settings()


def create_microsoft_state(*, user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload = {
        "sub": f"ms-connect:{user.email}",
        "uid": user.id,
        "typ": "ms_state",
        "nonce": secrets.token_urlsafe(16),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def validate_microsoft_state(state: str) -> int:
    payload = decode_token(state)
    if payload.get("typ") != "ms_state":
        raise ValueError("State inválido")

    user_id = payload.get("uid")
    if not user_id:
        raise ValueError("State sin usuario")

    return int(user_id)


def build_microsoft_authorization_url(*, state: str) -> str:
    base_url = f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/authorize"
    query = urlencode(
        {
            "client_id": settings.microsoft_client_id,
            "response_type": "code",
            "redirect_uri": settings.microsoft_redirect_uri,
            "response_mode": "query",
            "scope": settings.microsoft_scopes,
            "state": state,
        }
    )
    return f"{base_url}?{query}"


def exchange_code_for_tokens(*, code: str) -> dict[str, Any]:
    token_url = f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/token"
    payload = {
        "client_id": settings.microsoft_client_id,
        "client_secret": settings.microsoft_client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.microsoft_redirect_uri,
        "scope": settings.microsoft_scopes,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


def get_microsoft_profile(*, access_token: str) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            "https://graph.microsoft.com/v1.0/me?$select=id,displayName,mail,userPrincipalName",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


def upsert_linked_account(
    db: Session,
    *,
    user_id: int,
    tenant_id: str,
    token_payload: dict[str, Any],
    profile: dict[str, Any],
) -> LinkedAccount:
    account_email = profile.get("mail") or profile.get("userPrincipalName") or "sin-correo@microsoft.local"
    microsoft_user_id = profile["id"]
    display_name = profile.get("displayName") or account_email
    expires_in = int(token_payload.get("expires_in", 3600))
    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    account = (
        db.query(LinkedAccount)
        .filter(
            LinkedAccount.user_id == user_id,
            LinkedAccount.provider == "microsoft",
            LinkedAccount.microsoft_user_id == microsoft_user_id,
        )
        .first()
    )

    if account is None:
        account = LinkedAccount(
            user_id=user_id,
            provider="microsoft",
            account_email=account_email,
            display_name=display_name,
            microsoft_user_id=microsoft_user_id,
            tenant_id=tenant_id,
            access_token=token_payload["access_token"],
            refresh_token=token_payload.get("refresh_token") or "",
            token_expires_at=token_expires_at,
            is_active=True,
        )
        db.add(account)
    else:
        account.account_email = account_email
        account.display_name = display_name
        account.tenant_id = tenant_id
        account.access_token = token_payload["access_token"]
        account.refresh_token = token_payload.get("refresh_token") or account.refresh_token
        account.token_expires_at = token_expires_at
        account.is_active = True

    db.commit()
    db.refresh(account)
    return account


def list_user_linked_accounts(db: Session, *, user_id: int) -> list[LinkedAccount]:
    return (
        db.query(LinkedAccount)
        .filter(LinkedAccount.user_id == user_id)
        .order_by(LinkedAccount.created_at.desc())
        .all()
    )
def get_account_messages(*, access_token: str, top: int = 20) -> list[dict[str, Any]]:
    """
    Obtiene los correos del usuario desde Microsoft Graph
    """

    url = (
        "https://graph.microsoft.com/v1.0/me/messages"
        "?$select=id,subject,bodyPreview,receivedDateTime,from"
        f"&$top={top}"
        "&$orderby=receivedDateTime desc"
    )

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )

        response.raise_for_status()

        data = response.json()
        return data.get("value", [])