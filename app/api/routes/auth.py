"""Auth routes: signup, login. Users/me lives in users.py."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import security
from app.db.session import get_db
from app.models import User
from app.schemas import LoginIn, SignupIn, TokenOut, UserOut
from app.services import login as svc_login
from app.services import signup as svc_signup

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def signup(payload: SignupIn, db: Session = Depends(get_db)) -> User:
    return svc_signup(db, payload.name, str(payload.email), payload.password)


@router.post("/login", response_model=TokenOut, summary="Log in and receive a JWT")
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = svc_login(db, str(payload.email), payload.password)
    return TokenOut(access_token=security.create_access_token(str(user.id)))
