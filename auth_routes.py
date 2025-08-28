from fastapi import APIRouter, HTTPException, Response, Request, Depends, status
from fastapi.responses import JSONResponse
from models import *
from database import database, users_table, temp_registrations_table, temp_sessions_table, auth_sessions_table
from utils import *
from email_service import send_otp_email, send_otp_sms, send_admin_notification
from datetime import datetime
from typing import Optional, List
import uuid
import sqlalchemy

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Helper function to get temp_registration_id from cookie
def get_temp_registration_id(request: Request) -> Optional[str]:
    return request.cookies.get("temp_registration_id")

# Helper function to get temp_session_id from cookie
def get_temp_session_id(request: Request) -> Optional[str]:
    return request.cookies.get("temp_session_id")

# Helper function to get auth_session_id from cookie
def get_auth_session_id(request: Request) -> Optional[str]:
    return request.cookies.get("auth_session_id")

# Helper function to get current user from session
async def get_current_user(request: Request) -> Optional[dict]:
    """Get current user from auth session"""
    auth_session_id = get_auth_session_id(request)
    if not auth_session_id:
        return None
    
    # Check auth session
    query = sqlalchemy.select(auth_sessions_table).where(
        auth_sessions_table.c.session_token == auth_session_id
    )
    session = await database.fetch_one(query)
    
    if not session or is_expired(session.expires_at):
        return None
    
    # Get user
    user_query = sqlalchemy.select(users_table).where(
        users_table.c.id == session.user_id
    )
    user = await database.fetch_one(user_query)
    return user

# Helper function to check if user is admin
async def require_admin(request: Request):
    """Require admin role"""
    user = await get_current_user(request)
    if not user or user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"status": "error", "message": "Requires admin privileges"}
        )
    return user

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, response: Response):
    """Register a new user"""
    
    # Validate password confirmation
    if request.password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "Mật khẩu không trùng khớp"}
        )
    
    # Check if email or phone already exists
    query = sqlalchemy.select(users_table).where(
        sqlalchemy.or_(
            users_table.c.email == request.email,
            users_table.c.phone == request.phone
        )
    )
    existing_user = await database.fetch_one(query)
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"status": "error", "message": "Email hoặc số điện thoại đã được đăng kí"}
        )
    
    # Generate OTP and hash password
    otp = generate_otp()
    password_hash = hash_password(request.password)
    
    # Save temporary registration
    temp_reg_id = str(uuid.uuid4())
    temp_reg_data = {
        "id": temp_reg_id,
        "name": request.name,
        "email": request.email,
        "phone": request.phone,
        "password_hash": password_hash,
        "otp_code": otp,
        "otp_expires_at": get_otp_expiry()
    }
    
    # Delete any existing temp registration for this email/phone
    delete_query = sqlalchemy.delete(temp_registrations_table).where(
        sqlalchemy.or_(
            temp_registrations_table.c.email == request.email,
            temp_registrations_table.c.phone == request.phone
        )
    )
    await database.execute(delete_query)
    
    # Insert new temp registration
    insert_query = temp_registrations_table.insert().values(temp_reg_data)
    await database.execute(insert_query)
    
    # Set cookie
    response.set_cookie(
        key="temp_registration_id",
        value=temp_reg_id,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
        max_age=300  # 5 minutes
    )
    
    return RegisterResponse(
        status="Loading",
        message="Mã OTP đã gửi vào email mà bạn nhập. Vui lòng hoàn thiện quá trình đăng kí"
    )

@router.post("/verify-registration", response_model=RegisterSuccessResponse, status_code=status.HTTP_201_CREATED)
async def verify_registration(request: VerifyRegistrationRequest, http_request: Request, response: Response):
    """Verify registration OTP and create user"""
    
    temp_reg_id = get_temp_registration_id(http_request)
    if not temp_reg_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Chưa thấy đăng kí"}
        )
    
    # Get temp registration
    query = sqlalchemy.select(temp_registrations_table).where(
        temp_registrations_table.c.id == temp_reg_id
    )
    temp_reg = await database.fetch_one(query)
    
    if not temp_reg:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Chưa thấy đăng kí"}
        )
    
    # Check OTP and expiry
    if temp_reg.otp_code != request.otp or is_expired(temp_reg.otp_expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "Mã OTP đã hết hạn hoặc không tồn tại"}
        )
    
    # Create user (not approved yet)
    user_id = str(uuid.uuid4())
    user_data = {
        "id": user_id,
        "name": temp_reg.name,
        "email": temp_reg.email,
        "phone": temp_reg.phone,
        "password_hash": temp_reg.password_hash,
        "role": "user",
        "is_active": True,
        "is_approved": False  # Need admin approval
    }
    
    insert_user_query = users_table.insert().values(user_data)
    await database.execute(insert_user_query)
    
    # Send notification to admin about new registration
    admin_notification_data = {
        "name": temp_reg.name,
        "email": temp_reg.email,
        "phone": temp_reg.phone,
        "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }
    
    # Send admin notification (don't fail registration if email fails)
    try:
        await send_admin_notification(admin_notification_data)
    except Exception as e:
        print(f"Warning: Failed to send admin notification: {e}")
    
    # Delete temp registration
    delete_temp_query = sqlalchemy.delete(temp_registrations_table).where(
        temp_registrations_table.c.id == temp_reg_id
    )
    await database.execute(delete_temp_query)
    
    # Clear temp registration cookie
    response.delete_cookie(key="temp_registration_id", path="/")
    
    return RegisterSuccessResponse(
        status="success",
        message="Chúc mừng bạn đã đăng kí thành công! Vui lòng chờ admin phê duyệt.",
        user=UserResponse(
            id=user_id,
            name=temp_reg.name,
            email=temp_reg.email,
            phone=temp_reg.phone,
            role="user",
            is_approved=False
        )
    )

@router.post("/resend-registration-otp", response_model=SuccessResponse)
async def resend_registration_otp(request: Request):
    """Resend registration OTP"""
    
    temp_reg_id = get_temp_registration_id(request)
    if not temp_reg_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Không thấy đăng kí"}
        )
    
    # Get temp registration
    query = sqlalchemy.select(temp_registrations_table).where(
        temp_registrations_table.c.id == temp_reg_id
    )
    temp_reg = await database.fetch_one(query)
    
    if not temp_reg:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Không thấy đăng kí"}
        )
    
    # Generate new OTP
    new_otp = generate_otp()
    
    # Update temp registration with new OTP
    update_query = sqlalchemy.update(temp_registrations_table).where(
        temp_registrations_table.c.id == temp_reg_id
    ).values(
        otp_code=new_otp,
        otp_expires_at=get_otp_expiry()
    )
    await database.execute(update_query)
    
    # Send new OTP
    email_sent = await send_otp_email(temp_reg.email, new_otp, "registration")
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": "Không thể gửi email xác thực"}
        )
    
    return SuccessResponse(
        status="success",
        message="1 mã OTP mới được gửi đến email của bạn."
    )

@router.post("/login", response_model=LoginPendingResponse)
async def login(request: LoginRequest, response: Response):
    """Login user - step 1"""
    
    # Determine if identifier is email or phone
    if is_email(request.identifier):
        query = sqlalchemy.select(users_table).where(users_table.c.email == request.identifier)
    elif is_phone(request.identifier):
        query = sqlalchemy.select(users_table).where(users_table.c.phone == request.identifier)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "Định dạng email hoặc số điện thoại không hợp lệ"}
        )
    
    user = await database.fetch_one(query)
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Thông tin đăng nhập không chính xác"}
        )
    
    # Check if user is approved
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"status": "error", "message": "Tài khoản của bạn chưa được admin phê duyệt"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Tài khoản đã bị vô hiệu hóa"}
        )
    
    # Generate OTP and create temp session
    otp = generate_otp()
    temp_session_id = str(uuid.uuid4())
    
    # Delete any existing temp sessions for this user
    delete_query = sqlalchemy.delete(temp_sessions_table).where(
        temp_sessions_table.c.user_id == user.id
    )
    await database.execute(delete_query)
    
    # Create new temp session
    temp_session_data = {
        "id": temp_session_id,
        "user_id": user.id,
        "otp_code": otp,
        "otp_expires_at": get_otp_expiry()
    }
    
    insert_query = temp_sessions_table.insert().values(temp_session_data)
    await database.execute(insert_query)
    # Set cookie
    response.set_cookie(
        key="temp_session_id",
        value=temp_session_id,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
        max_age=300  # 5 minutes
    )
    
    return LoginPendingResponse(
        status="pending",
        message="OTP has been sent to your email or phone."
    )

@router.post("/verify-otp", response_model=LoginSuccessResponse)
async def verify_otp(request: VerifyOTPRequest, http_request: Request, response: Response):
    """Verify login OTP - step 2"""
    
    temp_session_id = get_temp_session_id(http_request)
    if not temp_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Phiên đăng nhập không hợp lệ"}
        )
    
    # Get temp session
    query = sqlalchemy.select(temp_sessions_table).where(
        temp_sessions_table.c.id == temp_session_id
    )
    temp_session = await database.fetch_one(query)
    
    if not temp_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Phiên đăng nhập không hợp lệ"}
        )
    
    # Check OTP and expiry
    if temp_session.otp_code != request.otp or is_expired(temp_session.otp_expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "Mã OTP không hợp lệ hoặc đã hết hạn"}
        )
    
    # Get user info
    user_query = sqlalchemy.select(users_table).where(
        users_table.c.id == temp_session.user_id
    )
    user = await database.fetch_one(user_query)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": "Người dùng không tồn tại"}
        )    # Create auth session
    auth_session_id = str(uuid.uuid4())
    session_token = generate_session_token()
    
    auth_session_data = {
        "id": auth_session_id,
        "user_id": user.id,
        "session_token": session_token,
        "expires_at": get_auth_session_expiry()
    }
    
    # Delete any existing auth sessions for this user
    delete_auth_query = sqlalchemy.delete(auth_sessions_table).where(
        auth_sessions_table.c.user_id == user.id
    )
    await database.execute(delete_auth_query)
    
    # Insert new auth session
    insert_auth_query = auth_sessions_table.insert().values(auth_session_data)
    await database.execute(insert_auth_query)
    
    # Delete temp session
    delete_temp_query = sqlalchemy.delete(temp_sessions_table).where(
        temp_sessions_table.c.id == temp_session_id
    )
    await database.execute(delete_temp_query)
    
    # Set auth cookie and clear temp cookie
    response.set_cookie(
        key="auth_session_id",
        value=session_token,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
        max_age=86400  # 24 hours
    )
    response.delete_cookie(key="temp_session_id", path="/")
    
    return LoginSuccessResponse(
        status="success",
        message="Login successful",
        user=UserResponse(
            id=str(user.id),
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            is_approved=user.is_approved
        )
    )

@router.post("/resend-otp", response_model=SuccessResponse)
async def resend_otp(request: Request):
    """Resend login OTP"""
    
    temp_session_id = get_temp_session_id(request)
    if not temp_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Phiên đăng nhập không hợp lệ"}
        )
    
    # Get temp session with user info
    query = sqlalchemy.select(temp_sessions_table).where(
        temp_sessions_table.c.id == temp_session_id
    )
    temp_session = await database.fetch_one(query)
    
    if not temp_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Phiên đăng nhập không hợp lệ"}
        )
    
    # Get user info
    user_query = sqlalchemy.select(users_table).where(
        users_table.c.id == temp_session.user_id
    )
    user = await database.fetch_one(user_query)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": "Người dùng không tồn tại"}
        )
    
    
    # Generate new OTP
    new_otp = generate_otp()
    
    # Update temp session with new OTP
    update_query = sqlalchemy.update(temp_sessions_table).where(
        temp_sessions_table.c.id == temp_session_id
    ).values(
        otp_code=new_otp,
        otp_expires_at=get_otp_expiry()
    )
    await database.execute(update_query)
    
    # Send new OTP to email (you can modify logic to determine email vs SMS)
    otp_sent = await send_otp_email(user.email, new_otp, "login")
    
    if not otp_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": "Không thể gửi mã OTP"}
        )
    
    return SuccessResponse(
        status="success",
        message="A new OTP has been sent to your email/phone."
    )

@router.post("/logout", response_model=SuccessResponse)
async def logout(request: Request, response: Response):
    """Logout user"""
    
    auth_session_id = get_auth_session_id(request)
    if auth_session_id:
        # Delete auth session from database
        delete_query = sqlalchemy.delete(auth_sessions_table).where(
            auth_sessions_table.c.session_token == auth_session_id
        )
        await database.execute(delete_query)
    
    # Clear cookie
    response.delete_cookie(key="auth_session_id", path="/")
    
    return SuccessResponse(
        status="success",
        message="Đăng xuất thành công"
    )

@router.delete("/admin/delete-user/{user_id}", response_model=AdminResponse)
async def delete_user(user_id: str, http_request: Request, admin_user = Depends(require_admin)):
    """Delete a user (Admin only)"""
    
    # Check if user exists
    user_query = sqlalchemy.select(users_table).where(
        users_table.c.id == user_id
    )
    user = await database.fetch_one(user_query)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": "Người dùng không tồn tại"}
        )
    
    # Delete user
    delete_query = sqlalchemy.delete(users_table).where(
        users_table.c.id == user_id
    )
    await database.execute(delete_query)
    
    return AdminResponse(
        status="success",
        message=f"Đã xóa người dùng {user.name}",
        data={"user_id": user_id, "user_name": user.name}
    )

# Session introspection
@router.get("/me", response_model=UserResponse)
async def me(request: Request):
    """Return current user if auth cookie is present and valid"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Chưa đăng nhập"}
        )
    return UserResponse(
        id=str(user.id),
        name=user.name,
        email=user.email,
        phone=user.phone,
        role=user.role,
        is_approved=user.is_approved,
    )

# Admin endpoints
@router.get("/admin/pending-users", response_model=List[UserListResponse])
async def get_pending_users(request: Request, admin_user = Depends(require_admin)):
    """Get list of users pending approval (Admin only)"""
    
    query = sqlalchemy.select(users_table).where(
        users_table.c.is_approved == False
    ).order_by(users_table.c.created_at.desc())
    
    users = await database.fetch_all(query)
    
    return [
        UserListResponse(
            id=str(user.id),
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            is_approved=user.is_approved,
            is_active=user.is_active,
            created_at=user.created_at
        )
        for user in users
    ]

@router.post("/admin/approve-user", response_model=AdminResponse)
async def approve_user(request: ApproveUserRequest, http_request: Request, admin_user = Depends(require_admin)):
    """Approve a user (Admin only)"""
    
    # Check if user exists
    user_query = sqlalchemy.select(users_table).where(
        users_table.c.id == request.user_id
    )
    user = await database.fetch_one(user_query)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": "Người dùng không tồn tại"}
        )
    
    if user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "Người dùng đã được phê duyệt"}
        )
    
    # Approve user
    update_query = users_table.update().where(
        users_table.c.id == request.user_id
    ).values(
        is_approved=True,
        approved_at=datetime.utcnow(),
        approved_by=admin_user.id
    )
    await database.execute(update_query)
    
    # Send approval email
    approval_sent = await send_otp_email(
        user.email, 
        "", 
        "approval"
    )
    
    return AdminResponse(
        status="success",
        message=f"Đã phê duyệt người dùng {user.name}",
        data={"user_id": request.user_id, "user_name": user.name}
    )

@router.get("/admin/all-users", response_model=List[UserListResponse])
async def get_all_users(request: Request, admin_user = Depends(require_admin)):
    """Get list of all users (Admin only)"""
    
    query = sqlalchemy.select(users_table).order_by(users_table.c.created_at.desc())
    users = await database.fetch_all(query)
    
    return [
        UserListResponse(
            id=str(user.id),
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            is_approved=user.is_approved,
            is_active=user.is_active,
            created_at=user.created_at
        )
        for user in users
    ]
