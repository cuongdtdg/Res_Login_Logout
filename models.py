from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import uuid
from datetime import datetime

# Registration models
class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., pattern=r'^[0-9]{10,11}$')
    password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

class VerifyRegistrationRequest(BaseModel):
    otp: str = Field(..., pattern=r'^[0-9]{6}$')

# Login models
class LoginRequest(BaseModel):
    identifier: str  # email or phone
    password: str

class VerifyOTPRequest(BaseModel):
    otp: str = Field(..., pattern=r'^[0-9]{6}$')

# Response models
class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    role: str
    is_approved: bool = False

class RegisterSuccessResponse(BaseModel):
    status: str
    message: str
    user: Optional[UserResponse] = None

class RegisterResponse(BaseModel):
    status: str
    message: str

class LoginPendingResponse(BaseModel):
    status: str
    message: str

class LoginSuccessResponse(BaseModel):
    status: str
    message: str
    user: UserResponse

class ErrorResponse(BaseModel):
    status: str
    message: str

class SuccessResponse(BaseModel):
    status: str
    message: str

# Admin models
class UserListResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    role: str
    is_approved: bool
    is_active: bool
    created_at: datetime

class ApproveUserRequest(BaseModel):
    user_id: str

class AdminResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None
