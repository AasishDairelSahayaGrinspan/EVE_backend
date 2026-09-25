"""Centre catalogue. Reads + writes require auth (no RBAC by design choice)."""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import NotFound
from app.db.session import get_db
from app.models import DiagnosticCentre, User
from app.schemas import CentreIn, CentreOut

router = APIRouter(prefix="/centres", tags=["centres"])


@router.get("", response_model=list[CentreOut], summary="List diagnostic centres")
def list_centres(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[DiagnosticCentre]:
    return db.query(DiagnosticCentre).order_by(DiagnosticCentre.created_at).offset(offset).limit(limit).all()


@router.get("/{centre_id}", response_model=CentreOut, summary="Get centre by id")
def get_centre(
    centre_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DiagnosticCentre:
    centre = db.get(DiagnosticCentre, centre_id)
    if centre is None:
        raise NotFound("Diagnostic centre not found")
    return centre


@router.post("", response_model=CentreOut, status_code=status.HTTP_201_CREATED, summary="Create centre")
def create_centre(
    payload: CentreIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DiagnosticCentre:
    centre = DiagnosticCentre(name=payload.name.strip(), location=payload.location.strip())
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


@router.patch("/{centre_id}", response_model=CentreOut, summary="Update centre")
def update_centre(
    centre_id: uuid.UUID,
    payload: CentreIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DiagnosticCentre:
    centre = db.get(DiagnosticCentre, centre_id)
    if centre is None:
        raise NotFound("Diagnostic centre not found")
    centre.name = payload.name.strip()
    centre.location = payload.location.strip()
    db.commit()
    db.refresh(centre)
    return centre
