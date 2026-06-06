from pydantic import EmailStr, Field

from app.schemas.common import CamelModel


class RegisterIn(CamelModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(CamelModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserOut(CamelModel):
    id: str
    email: str
    name: str


class AuthOut(CamelModel):
    token: str
    user: UserOut
