from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import List, Optional
from enum import Enum


# ✅ Signup Schema (Input)
class UserSignup(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    country_code: Optional[str] = None
    password: str
    send_email_verification: Optional[bool] = True


class UserEmailLogin(BaseModel):
    email: str  # ✅ This expects email in our case
    password: str


class EmailOTPRequest(BaseModel):
    email: EmailStr


class EmailOTPVerification(BaseModel):
    email: EmailStr
    otp: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str
    token: str


class PhoneVerificationRequest(BaseModel):
    phone_number: str
    country_code: str


class PhoneOTPVerification(BaseModel):
    phone_number: str
    country_code: str
    otp: str


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    country_code: Optional[str] = None


# OTP Verification Schema (Input)
class OTPVerification(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=15, example="+1234567890")
    otp: str = Field(..., min_length=6, max_length=6, example="123456")


# ✅ Response Model for User Data (Output)
class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: str
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True  # ✅ Enables conversion from SQLAlchemy model


# ✅ Response Model for Signup/Login Success
class AuthResponse(BaseModel):
    message: str
    access_token: Optional[str] = None
    token_type: str = "bearer"


# ✅ Response Model for OTP Success
class OTPResponse(BaseModel):
    message: str


class UserProfileUpdate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, example="John Doe")
    email: EmailStr = Field(..., example="user@example.com")
    brokerAccounts: str = Field(..., example="Zerodha, Upstox")


class UserRole(str, Enum):
    ADMIN = "admin"
    TRADER = "trader"
    ANALYST = "analyst"


class BrokerAccountResponse(BaseModel):
    id: int
    broker_name: str
    is_active: bool
    created_at: datetime
    last_connected: Optional[datetime] = None

    class Config:
        from_attributes = True


class BrokerConfigResponse(BaseModel):
    id: int
    broker_name: str
    client_id: Optional[str] = None
    is_active: bool
    access_token_expiry: Optional[datetime] = None
    access_token: Optional[str] = None  # Included as frontend checks for its presence
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: Optional[str]
    country_code: Optional[str]
    role: UserRole
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    broker_accounts: List[BrokerAccountResponse] = []
    total_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0

    class Config:
        from_attributes = True


class UserProfileUpdateExtended(BaseModel):  # Renamed to avoid conflict
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = Field(
        None, pattern=r"^\+?[1-9]\d{1,14}$"
    )  # Fixed: = instead of ==
    country_code: Optional[str] = Field(None, min_length=1, max_length=5)

    @field_validator("full_name")
    @classmethod  # This should be inside the class
    def validate_full_name(cls, v):
        if v and not v.strip():
            raise ValueError("Full name cannot be empty")
        return v.strip() if v else v


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):  # Pydantic v2 uses 'info' instead of 'values'
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class UserStatsResponse(BaseModel):
    total_trades: int
    successful_trades: int
    total_pnl: float
    win_rate: float
    best_performing_stock: Optional[str]
    worst_performing_stock: Optional[str]
    avg_trade_duration: Optional[float]  # in hours
    last_trade_date: Optional[datetime]


class NotificationResponse(BaseModel):
    id: int
    message: str
    type: str
    read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True
