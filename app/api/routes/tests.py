"""Test catalogue + offerings wiring (which centre offers which test at what price)."""
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import BadRequest, Conflict, NotFound
from app.db.session import get_db
from app.models import CentreOffering, DiagnosticCentre, DiagnosticTest, User
from app.schemas import OfferingIn, OfferingOut, TestIn, TestOut

router = APIRouter(tags=["tests"])


@router.get("/tests", response_model=list[TestOut], summary="List diagnostic tests")
def list_tests(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[DiagnosticTest]:
    return db.query(DiagnosticTest).order_by(DiagnosticTest.created_at).offset(offset).limit(limit).all()


@router.get("/tests/{test_id}", response_model=TestOut, summary="Get test by id")
def get_test(
    test_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DiagnosticTest:
    test = db.get(DiagnosticTest, test_id)
    if test is None:
        raise NotFound("Diagnostic test not found")
    return test


@router.post("/tests", response_model=TestOut, status_code=status.HTTP_201_CREATED, summary="Create test")
def create_test(
    payload: TestIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DiagnosticTest:
    test = DiagnosticTest(name=payload.name.strip(), description=payload.description)
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@router.patch("/tests/{test_id}", response_model=TestOut, summary="Update test")
def update_test(
    test_id: uuid.UUID,
    payload: TestIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DiagnosticTest:
    test = db.get(DiagnosticTest, test_id)
    if test is None:
        raise NotFound("Diagnostic test not found")
    test.name = payload.name.strip()
    test.description = payload.description
    db.commit()
    db.refresh(test)
    return test


@router.post(
    "/offerings",
    response_model=OfferingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Offer a test at a centre with a price",
)
def upsert_offering(
    payload: OfferingIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CentreOffering:
    if db.get(DiagnosticCentre, payload.centre_id) is None:
        raise NotFound("Diagnostic centre not found")
    if db.get(DiagnosticTest, payload.test_id) is None:
        raise NotFound("Diagnostic test not found")
    existing = (
        db.query(CentreOffering)
        .filter(
            CentreOffering.centre_id == payload.centre_id,
            CentreOffering.test_id == payload.test_id,
        )
        .first()
    )
    if existing:
        existing.price = payload.price
        existing.is_available = payload.is_available
        db.commit()
        db.refresh(existing)
        return existing
    offering = CentreOffering(
        centre_id=payload.centre_id,
        test_id=payload.test_id,
        price=payload.price,
        is_available=payload.is_available,
    )
    db.add(offering)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict("Offering already exists")
    db.refresh(offering)
    return offering
