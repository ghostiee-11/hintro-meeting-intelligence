from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, rate_limit
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import AuthOut, LoginIn, RegisterIn, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthOut,
    status_code=201,
    dependencies=[Depends(rate_limit(10, 60))],
)
async def register(payload: RegisterIn, db: DbSession) -> AuthOut:
    existing = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise AppError.conflict("An account with this email already exists")

    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    token = create_access_token(user.id, user.email)
    return AuthOut(token=token, user=UserOut(id=user.id, email=user.email, name=user.name))


@router.post("/login", response_model=AuthOut, dependencies=[Depends(rate_limit(10, 60))])
async def login(payload: LoginIn, db: DbSession) -> AuthOut:
    user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError.unauthorized("Invalid email or password")
    token = create_access_token(user.id, user.email)
    return AuthOut(token=token, user=UserOut(id=user.id, email=user.email, name=user.name))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name)
