"""Booking routes. Price/status are server-controlled; clients only pick centre/test/time."""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Booking, User
from app.schemas import BookingIn, BookingOut
from app.services import cancel_booking as svc_cancel
from app.services import create_booking as svc_create
from app.services import get_owned_booking as svc_get

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("", response_model=list[BookingOut], summary="List my bookings")
def list_bookings(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.user_id == user.id)
        .order_by(Booking.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{booking_id}", response_model=BookingOut, summary="Get my booking by id")
def get_booking(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Booking:
    return svc_get(db, user, booking_id)


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED, summary="Create booking")
def create_booking(
    payload: BookingIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Booking:
    return svc_create(db, user, payload.centre_id, payload.test_id, payload.appointment_at)


@router.post("/{booking_id}/cancel", response_model=BookingOut, summary="Cancel my booking")
def cancel_booking(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Booking:
    return svc_cancel(db, user, booking_id)
