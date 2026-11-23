"""Esquemas definidos en el contrato OpenAPI (components/schemas)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objectId: str
    userId: str
    verified: Literal[True] = True


ProblemCode = Literal[
    "UNAUTHENTICATED",
    "OBJECT_NOT_FOUND",
    "OBJECT_ALREADY_CLAIMED",
    "IDENTITY_NOT_VERIFIED",
    "IDEMPOTENCY_KEY_REUSED",
    "INVALID_IDEMPOTENCY_KEY",
    "INVALID_CREDENTIALS",
    "AUTH_NOT_CONFIGURED",
    "VALIDATION_ERROR",
    "FORBIDDEN",
]


class Problem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ProblemCode
    message: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accessToken: str
    tokenType: Literal["bearer"] = "bearer"
    expiresIn: int


class CreateObjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)


class LostObjectOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str | None = None
    reportedBy: str | None = None
    claimedBy: str | None = None


class InventoryItem(BaseModel):
    id: str
    name: str
    description: str | None
    status: Literal["available", "claimed", "approved", "delivered"]
    claimedBy: str | None = None
    foundAt: str | None = None
    location: str | None = None
    photoUrl: str | None = None
    receivedAt: str | None = None
    history: list[dict[str, str]] = Field(default_factory=list)


class IntakeRequest(CreateObjectRequest):
    foundAt: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=160)
    photoUrl: HttpUrl | None = None


class ReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(default="", max_length=500)


class SuspensionRequest(BaseModel):
    suspended: bool
