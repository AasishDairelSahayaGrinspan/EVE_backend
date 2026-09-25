"""Current-user route."""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models import User
from app.schemas import UserOut

router = APIRouter(tags=["users"])


@router.get("/users/me", response_model=UserOut, summary="Get current user")
def me(user: User = Depends(get_current_user)) -> User:
    return user
