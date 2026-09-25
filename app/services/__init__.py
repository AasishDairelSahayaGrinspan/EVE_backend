"""Auth + booking + payment domain logic. Routes stay thin; transactions live here."""
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import security
from app.core.exceptions import BadRequest, Conflict, Forbidden, NotFound
from app.models import (
    Booking,
    BookingStatus,
    CentreOffering,
    DiagnosticCentre,
    DiagnosticTest,
    Payment,
    PaymentStatus,
    User,
    WebhookEvent,
)

# ---- state machine: allowed transitions ----
ALLOWED: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.PENDING: {BookingStatus.CONFIRMED, BookingStatus.FAILED, BookingStatus.CANCELLED},
    BookingStatus.CONFIRMED: {BookingStatus.CANCELLED},
    BookingStatus.FAILED: set(),
    BookingStatus.CANCELLED: set(),
}


def _check_transition(current: BookingStatus, target: BookingStatus) -> None:
    if target not in ALLOWED[current]:
        raise Conflict(f"Invalid status transition {current.value} -> {target.value}")


# ---- auth ----
def signup(db: Session, name: str, email: str, password: str) -> User:
    email_norm = email.strip().lower()
    if db.query(User).filter(User.email == email_norm).first():
        raise Conflict("Email already registered")
    user = User(name=name.strip(), email=email_norm, password_hash=security.hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict("Email already registered")
    db.refresh(user)
    return user


def login(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if user is None or not security.verify_password(password, user.password_hash):
        from app.core.exceptions import Unauthorized

        raise Unauthorized("Invalid email or password")
    return user


# ---- bookings ----
def create_booking(
    db: Session, user: User, centre_id, test_id, appointment_at: datetime
) -> Booking:
    if appointment_at.tzinfo is None:
        appointment_at = appointment_at.replace(tzinfo=timezone.utc)
    if appointment_at <= datetime.now(timezone.utc):
        raise BadRequest("appointment_at must be in the future")

    centre = db.get(DiagnosticCentre, centre_id)
    if centre is None:
        raise NotFound("Diagnostic centre not found")
    test = db.get(DiagnosticTest, test_id)
    if test is None:
        raise NotFound("Diagnostic test not found")
    offering = (
        db.query(CentreOffering)
        .filter(CentreOffering.centre_id == centre_id, CentreOffering.test_id == test_id)
        .first()
    )
    if offering is None or not offering.is_available:
        raise BadRequest("Test is not offered by the selected centre")

    # Price snapshot: copied now so later price edits don't affect this booking.
    booking = Booking(
        user_id=user.id,
        centre_id=centre_id,
        test_id=test_id,
        appointment_at=appointment_at,
        amount=offering.price,
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_owned_booking(db: Session, user: User, booking_id) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise NotFound("Booking not found")
    if booking.user_id != user.id:
        raise Forbidden("Booking does not belong to the authenticated user")
    return booking


def cancel_booking(db: Session, user: User, booking_id) -> Booking:
    booking = db.get(Booking, booking_id, with_for_update=True)
    if booking is None:
        raise NotFound("Booking not found")
    if booking.user_id != user.id:
        raise Forbidden("Booking does not belong to the authenticated user")
    _check_transition(booking.status, BookingStatus.CANCELLED)
    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return booking


# ---- payments (simulated) ----
def initiate_payment(
    db: Session, user: User, booking_id, simulate_outcome: str | None
) -> Payment:
    outcome = (simulate_outcome or "SUCCESS").upper()
    if outcome not in {"SUCCESS", "FAILED"}:
        raise BadRequest("simulate_outcome must be SUCCESS or FAILED")

    booking = db.get(Booking, booking_id, with_for_update=True)
    if booking is None:
        raise NotFound("Booking not found")
    if booking.user_id != user.id:
        raise Forbidden("Booking does not belong to the authenticated user")
    if booking.status != BookingStatus.PENDING:
        raise Conflict(f"Booking is {booking.status.value} and cannot be paid")

    import uuid as _uuid

    payment = Payment(
        booking_id=booking.id,
        provider_payment_id=f"pay_{_uuid.uuid4().hex[:16]}",
        amount=booking.amount,  # server-derived, never from client
        status=PaymentStatus.SUCCESS if outcome == "SUCCESS" else PaymentStatus.FAILED,
    )
    booking.status = (
        BookingStatus.CONFIRMED if outcome == "SUCCESS" else BookingStatus.FAILED
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


# ---- webhook (idempotent) ----
def handle_webhook(
    db: Session,
    *,
    event_id: str,
    event_type: str,
    provider_payment_id: str,
    booking_id,
    amount,
    status: str,
) -> dict:
    from datetime import datetime, timezone

    # Fast-path dedupe before locking anything.
    existing = db.query(WebhookEvent).filter(WebhookEvent.external_event_id == event_id).first()
    if existing is not None:
        return {"deduped": True, "event_id": event_id}

    booking = db.get(Booking, booking_id, with_for_update=True)
    if booking is None:
        raise NotFound("Booking not found")

    payment = (
        db.query(Payment).filter(Payment.provider_payment_id == provider_payment_id).first()
    )
    if payment is not None and payment.booking_id != booking.id:
        raise Conflict("payment_id belongs to a different booking")
    if payment is not None and payment.amount != amount:
        raise Conflict("Webhook amount does not match payment amount")

    target = BookingStatus.CONFIRMED if status == "SUCCESS" else BookingStatus.FAILED

    # Terminal states win: never resurrect CANCELLED/FAILED via a late SUCCESS.
    if booking.status in {BookingStatus.CANCELLED, BookingStatus.FAILED}:
        if booking.status != target:
            event = WebhookEvent(
                external_event_id=event_id,
                event_type=event_type,
                booking_id=booking.id,
                provider_payment_id=provider_payment_id,
                payload={"note": "late webhook ignored; booking terminal"},
                processed=True,
                processed_at=datetime.now(timezone.utc),
            )
            db.add(event)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()  # concurrent duplicate won the race
                return {"deduped": True, "event_id": event_id}
            return {"deduped": False, "event_id": event_id, "ignored": "terminal state"}
        # same-state redelivery: record event, no state change
    elif booking.status == target:
        pass  # idempotent redelivery with a new event_id; state already correct
    else:
        _check_transition(booking.status, target)
        booking.status = target

    if payment is None:
        payment = Payment(
            booking_id=booking.id,
            provider_payment_id=provider_payment_id,
            amount=amount,
            status=PaymentStatus.SUCCESS if status == "SUCCESS" else PaymentStatus.FAILED,
        )
        db.add(payment)
    else:
        payment.status = PaymentStatus.SUCCESS if status == "SUCCESS" else PaymentStatus.FAILED

    event = WebhookEvent(
        external_event_id=event_id,
        event_type=event_type,
        booking_id=booking.id,
        provider_payment_id=provider_payment_id,
        payload={
            "event_type": event_type,
            "payment_id": provider_payment_id,
            "amount": str(amount),
            "status": status,
        },
        processed=True,
        processed_at=datetime.now(timezone.utc),
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        # Two identical webhooks raced: UNIQUE on external_event_id fired.
        db.rollback()
        return {"deduped": True, "event_id": event_id}
    return {"deduped": False, "event_id": event_id}
