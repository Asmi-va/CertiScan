"""
Authentication API endpoints.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr

from app.services.auth_service import auth_service
from app.middleware.auth_middleware import (
    get_current_user, get_current_active_user, require_2fa, get_request_context
)
from app.db.models import UserCreate, UserResponse, UserRole

router = APIRouter()

# Request/Response models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserResponse
    two_factor_required: bool

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TwoFactorRequest(BaseModel):
    user_id: str
    token: str

class TwoFactorSetupResponse(BaseModel):
    secret: str
    qr_code: str
    message: str

class EnableTwoFactorRequest(BaseModel):
    token: str

class DisableTwoFactorRequest(BaseModel):
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class MessageResponse(BaseModel):
    message: str

@router.post("/register", response_model=Dict[str, Any])
async def register_user(
    user_data: UserCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Register a new user. Requires admin or institution admin privileges."""
    # Check permissions
    if current_user["role"] not in [UserRole.ADMIN, UserRole.INSTITUTION]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to register users"
        )
    
    # Institution users can only create users for their own institution
    if current_user["role"] == UserRole.INSTITUTION:
        if user_data.institution_id != current_user.get("institution_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only register users for your own institution"
            )
    
    context = await get_request_context(request)
    
    return await auth_service.register_user(
        user_data=user_data,
        created_by=current_user["user_id"],
        ip_address=context["ip_address"]
    )

@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request
):
    """Authenticate user and return access tokens."""
    context = await get_request_context(request)
    
    return await auth_service.authenticate_user(
        email=login_data.email,
        password=login_data.password,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"]
    )

@router.post("/verify-2fa", response_model=TokenResponse)
async def verify_two_factor(
    two_factor_data: TwoFactorRequest,
    request: Request
):
    """Verify 2FA token and complete login."""
    context = await get_request_context(request)
    
    return await auth_service.verify_2fa_and_complete_login(
        user_id=two_factor_data.user_id,
        token=two_factor_data.token,
        ip_address=context["ip_address"]
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """Refresh access token using refresh token."""
    return await auth_service.refresh_access_token(refresh_data.refresh_token)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_active_user)
):
    """Get current user information."""
    return UserResponse(**current_user)

@router.post("/setup-2fa", response_model=TwoFactorSetupResponse)
async def setup_two_factor_auth(
    current_user: dict = Depends(get_current_active_user)
):
    """Set up two-factor authentication for current user."""
    return await auth_service.setup_2fa(current_user["user_id"])

@router.post("/enable-2fa", response_model=MessageResponse)
async def enable_two_factor_auth(
    enable_data: EnableTwoFactorRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Enable two-factor authentication after setup verification."""
    return await auth_service.enable_2fa(
        user_id=current_user["user_id"],
        token=enable_data.token
    )

@router.post("/disable-2fa", response_model=MessageResponse)
async def disable_two_factor_auth(
    disable_data: DisableTwoFactorRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Disable two-factor authentication."""
    return await auth_service.disable_2fa(
        user_id=current_user["user_id"],
        password=disable_data.password
    )

@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Change user password."""
    return await auth_service.change_password(
        user_id=current_user["user_id"],
        current_password=password_data.current_password,
        new_password=password_data.new_password
    )

@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    """Logout user (client should discard tokens)."""
    from app.db.utils import DatabaseUtils
    
    context = await get_request_context(request)
    
    # Create audit log
    await DatabaseUtils.create_audit_log(
        user_id=current_user["user_id"],
        action="LOGOUT",
        resource_type="user",
        resource_id=current_user["user_id"],
        ip_address=context["ip_address"],
        user_agent=context["user_agent"]
    )
    
    return {"message": "Logged out successfully"}

@router.get("/permissions")
async def get_user_permissions(
    current_user: dict = Depends(get_current_active_user)
):
    """Get current user's permissions."""
    from app.core.security import get_user_permissions
    
    user_role = UserRole(current_user["role"])
    permissions = get_user_permissions(user_role)
    
    return {
        "user_id": current_user["user_id"],
        "role": current_user["role"],
        "permissions": permissions
    }

@router.get("/validate-token")
async def validate_token(
    current_user: dict = Depends(get_current_active_user)
):
    """Validate current token and return user info."""
    token_claims = current_user.get("token_claims", {})
    
    return {
        "valid": True,
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "role": current_user["role"],
        "expires_at": token_claims.get("exp"),
        "two_factor_verified": token_claims.get("two_factor_verified", False)
    }

# Admin-only endpoints
@router.get("/users", response_model=Dict[str, Any])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_active_user)
):
    """List users (admin only)."""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # This would be implemented with proper user listing logic
    return {
        "message": "User listing endpoint - to be implemented",
        "skip": skip,
        "limit": limit
    }

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    current_user: dict = Depends(get_current_active_user)
):
    """Update user active status (admin only)."""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    from app.db.utils import user_repo, DatabaseUtils
    
    # Update user status
    success = await user_repo.update(user_id, {"is_active": is_active})
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create audit log
    await DatabaseUtils.create_audit_log(
        user_id=current_user["user_id"],
        action="UPDATE_USER_STATUS",
        resource_type="user",
        resource_id=user_id,
        details={"is_active": is_active}
    )
    
    return {
        "message": f"User {'activated' if is_active else 'deactivated'} successfully"
    }