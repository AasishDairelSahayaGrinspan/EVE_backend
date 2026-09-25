"""Simulated payments. Deterministic via simulate_outcome (for tests/demos)."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Payment, User
from app.schemas import PaymentIn, PaymentOut
from app.services import initiate_payment as svc_pay

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "/",
    response_model=PaymentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Pay for my booking (simulated)",
)
def create_payment(
    payload: PaymentIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Payment:
    return svc_pay(db, user, payload.booking_id, payload.simulate_outcome)
