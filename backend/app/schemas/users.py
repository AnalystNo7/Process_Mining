from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: str | None = None
    email: EmailStr | None = None
    role: Literal["admin", "analyst"]
    is_ldap: bool = False


class UserCreate(UserBase):
    password: str | None = Field(default=None, min_length=8)


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    role: Literal["admin", "analyst"] | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class UserList(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
