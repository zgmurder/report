from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    roles: list[str]
    unit_code: str | None = None
    status: str


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=120)
    roles: list[str] = Field(default_factory=lambda: ["user"])
    unit_code: str | None = Field(default=None, max_length=32)
    status: str = Field(default="enabled", max_length=20)


class UserUpdateRequest(BaseModel):
    password: str | None = Field(default=None, min_length=6, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    roles: list[str] | None = None
    unit_code: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=20)
