from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.ml.classifier import MODEL_VERSION, classify_email
from app.models.linked_account import LinkedAccount
from app.models.user import User
from app.schemas.email import (
    EmailCategoryUpdate,
    EmailChatbotQuery,
    EmailChatbotResponse,
    EmailClassifyIn,
    EmailClassifyResponse,
    EmailOut,
)
from app.services.email_service import (
    chatbot_email_query,
    create_classified_email,
    get_global_advanced_statistics,
    get_user_email_by_id,
    list_user_emails,
    list_user_emails_by_account,
    list_user_emails_by_category,
    sync_emails_from_microsoft_account,
    update_email_category,
)

router = APIRouter(prefix="/emails", tags=["Emails"])

CONFIDENCE_THRESHOLD = 0.30


@router.post("/classify", response_model=EmailClassifyResponse, status_code=status.HTTP_201_CREATED)
def classify_and_save_email(
    payload: EmailClassifyIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailClassifyResponse:
    category, confidence = classify_email(payload.subject, payload.body)

    if confidence < CONFIDENCE_THRESHOLD:
        category = "otros"

    email = create_classified_email(
        db,
        owner=current_user,
        subject=payload.subject,
        body=payload.body,
        sender=payload.sender,
        source_account=payload.source_account,
        predicted_category=category,
        confidence=confidence,
    )
    return EmailClassifyResponse(email=email, model_version=MODEL_VERSION)


@router.get("/mine", response_model=list[EmailOut])
def read_my_emails(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmailOut]:
    return list_user_emails(db, owner=current_user)


@router.get("/mine/category/{category}", response_model=list[EmailOut])
def read_my_emails_by_category(
    category: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmailOut]:
    return list_user_emails_by_category(
        db,
        owner=current_user,
        category=category,
    )


@router.get("/stats/advanced")
def get_advanced_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "secretaria")),
):
    return get_global_advanced_statistics(db)


@router.post("/chatbot/query", response_model=EmailChatbotResponse)
def chatbot_query_endpoint(
    payload: EmailChatbotQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailChatbotResponse:
    result = chatbot_email_query(
        db,
        owner=current_user,
        user_query=payload.query,
    )
    return EmailChatbotResponse(**result)


@router.get("/mine/account/{account_id}", response_model=list[EmailOut])
def read_my_emails_by_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmailOut]:
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

    return list_user_emails_by_account(
        db,
        owner=current_user,
        linked_account_id=account_id,
    )


@router.post("/sync/{account_id}")
def sync_my_microsoft_emails(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = (
        db.query(LinkedAccount)
        .filter(
            LinkedAccount.id == account_id,
            LinkedAccount.user_id == current_user.id,
            LinkedAccount.is_active == True,
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=404,
            detail="Cuenta Microsoft no encontrada o inactiva",
        )

    saved = sync_emails_from_microsoft_account(
        db,
        owner=current_user,
        account=account,
        top=20,
    )

    return {
        "message": "Sincronización completada",
        "account_id": account.id,
        "account_email": account.account_email,
        "synced_count": len(saved),
    }


@router.get("/{email_id}", response_model=EmailOut)
def read_my_email_detail(
    email_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailOut:
    email = get_user_email_by_id(db, owner=current_user, email_id=email_id)

    if not email:
        raise HTTPException(status_code=404, detail="Correo no encontrado")

    return email


@router.put("/{email_id}/category", response_model=EmailOut)
def update_email_category_endpoint(
    email_id: int,
    payload: EmailCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailOut:
    email = update_email_category(
        db,
        owner=current_user,
        email_id=email_id,
        new_category=payload.category,
    )

    if not email:
        raise HTTPException(status_code=404, detail="Correo no encontrado")

    return email