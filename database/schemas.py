from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


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


class OTPVerification(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=5, example="+1")
    phone_number: str = Field(..., min_length=10, max_length=15, example="9876543210")
    otp: str = Field(..., min_length=6, max_length=6, example="123456")


class UserProfileUpdate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, example="John Doe")
    email: EmailStr = Field(..., example="user@example.com")
    brokerAccounts: str = Field(..., example="Zerodha, Upstox")
