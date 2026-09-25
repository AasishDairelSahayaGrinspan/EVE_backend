"""Pydantic request/response schemas. Never expose password hashes or internal rows."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import BookingStatus, PaymentStatus


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120, examples=["Aarav Sharma"])
    email: EmailStr = Field(examples=["aarav@example.com"])
    password: str = Field(min_length=8, max_length=128, examples=["s3cure-pass"])


class LoginIn(BaseModel):
    email: EmailStr = Field(examples=["aarav@example.com"])
    password: str = Field(min_length=1, examples=["s3cure-pass"])


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    email: str
    created_at: datetime


class CentreIn(BaseModel):
    name: str = Field(min_length=1, max_length=200, examples=["CityCare Diagnostics"])
    location: str = Field(min_length=1, max_length=300, examples=["Indiranagar, Bengaluru"])


class CentreOut(CentreIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime


class TestIn(BaseModel):
    name: str = Field(min_length=1, max_length=200, examples=["Lipid Profile"])
    description: str | None = Field(default=None, examples=["Fasting cholesterol panel"])


class TestOut(TestIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime


class OfferingIn(BaseModel):
    centre_id: uuid.UUID
    test_id: uuid.UUID
    price: Decimal = Field(ge=0, examples=["499.00"])
    is_available: bool = True


class OfferingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    centre_id: uuid.UUID
    test_id: uuid.UUID
    price: Decimal
    is_available: bool


class BookingIn(BaseModel):
    centre_id: uuid.UUID
    test_id: uuid.UUID
    appointment_at: datetime = Field(examples=["2030-05-01T10:00:00Z"])

    model_config = ConfigDict(json_schema_extra={"required": ["centre_id", "test_id"]})


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    centre_id: uuid.UUID
    test_id: uuid.UUID
    appointment_at: datetime
    amount: Decimal
    status: BookingStatus
    created_at: datetime


class PaymentIn(BaseModel):
    booking_id: uuid.UUID
    # Deterministic simulator for tests/demos. In prod this would call a PSP.
    simulate_outcome: Literal["SUCCESS", "FAILED"] | None = Field(
        default=None, examples=["SUCCESS"]
    )


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    booking_id: uuid.UUID
    provider_payment_id: str
    amount: Decimal
    status: PaymentStatus


class WebhookIn(BaseModel):
    event_id: str = Field(min_length=1, max_length=100, examples=["evt_123"])
    event_type: str = Field(min_length=1, max_length=100, examples=["payment.succeeded"])
    payment_id: str = Field(min_length=1, max_length=100, examples=["pay_123"])
    booking_id: uuid.UUID
    amount: Decimal = Field(ge=0, examples=["499.00"])
    status: Literal["SUCCESS", "FAILED"]
