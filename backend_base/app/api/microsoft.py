import httpx

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.linked_account import LinkedAccount
from app.models.user import User
from app.schemas.microsoft import (
    MicrosoftAccountOut,
    MicrosoftCallbackResponse,
    MicrosoftConnectResponse,
)
from app.services.microsoft_graph_service import (
    build_microsoft_authorization_url,
    create_microsoft_state,
    exchange_code_for_tokens,
    get_microsoft_profile,
    list_user_linked_accounts,
    upsert_linked_account,
    validate_microsoft_state,
)

router = APIRouter(prefix="/microsoft", tags=["Microsoft"])


@router.get("/connect", response_model=MicrosoftConnectResponse)
def connect_microsoft(
    current_user: User = Depends(get_current_user),
) -> MicrosoftConnectResponse:
    from app.core.config import get_settings

    settings = get_settings()
    state = create_microsoft_state(user=current_user)
    authorization_url = build_microsoft_authorization_url(state=state)

    return MicrosoftConnectResponse(
        authorization_url=authorization_url,
        state=state,
        redirect_uri=settings.microsoft_redirect_uri,
        scopes=settings.microsoft_scope_list,
    )


@router.get("/callback", response_model=MicrosoftCallbackResponse)
def microsoft_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> MicrosoftCallbackResponse:
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Microsoft devolvió error: {error}",
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falta code o state en el callback",
        )

    try:
        user_id = validate_microsoft_state(state)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        token_payload = exchange_code_for_tokens(code=code)
        profile = get_microsoft_profile(access_token=token_payload["access_token"])
        tenant_id = (
            token_payload.get("id_token_claims", {}).get("tid")
            or token_payload.get("tid")
            or "common"
        )

        account = upsert_linked_account(
            db=db,
            user_id=user_id,
            tenant_id=tenant_id,
            token_payload=token_payload,
            profile=profile,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error HTTP con Microsoft: {exc.response.text}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo vincular la cuenta Microsoft: {exc}",
        ) from exc

    return MicrosoftCallbackResponse(
        message="Cuenta Microsoft vinculada correctamente",
        account=account,
    )


@router.get("/accounts", response_model=list[MicrosoftAccountOut])
def read_my_microsoft_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MicrosoftAccountOut]:
    return list_user_linked_accounts(db=db, user_id=current_user.id)


@router.post("/accounts/{account_id}/disconnect")
def disconnect_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = (
        db.query(LinkedAccount)
        .filter(
            LinkedAccount.id == account_id,
            LinkedAccount.user_id == current_user.id,
        )
        .first()
    )

    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    account.is_active = False

    db.commit()
    db.refresh(account)

    return {"message": "Cuenta Microsoft desconectada correctamente"}