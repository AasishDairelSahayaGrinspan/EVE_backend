"""Payment webhook. MUST stay idempotent: UNIQUE(event_id) + transaction + safe transitions."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import WebhookIn
from app.services import handle_webhook as svc_webhook

router = APIRouter(prefix="/payments/webhook", tags=["webhooks"])


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Receive payment provider webhook (idempotent)",
)
def webhook(payload: WebhookIn, db: Session = Depends(get_db)) -> dict:
    return svc_webhook(
        db,
        event_id=payload.event_id,
        event_type=payload.event_type,
        provider_payment_id=payload.payment_id,
        booking_id=payload.booking_id,
        amount=payload.amount,
        status=payload.status,
    )
