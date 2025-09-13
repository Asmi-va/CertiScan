"""
Authentication service for user management and authentication.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import logging

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import (
    verify_password, get_password_hash, create_access_token, create_refresh_token,
    verify_token, generate_2fa_secret, verify_2fa_token, generate_session_id,
    validate_password, is_account_locked, calculate_lockout_time,
    AuthenticationError, AuthorizationError, rate_limiter
)
from app.db.models import User, UserRole, UserCreate, UserResponse
from app.db.utils import user_repo, DatabaseUtils

logger = logging.getLogger(__name__)

class AuthService:
    """Service for handling authentication and user management."""
    
    def __init__(self):
        self.max_login_attempts = 5
        self.login_rate_limit = 10  # requests per minute
    
    async def register_user(
        self, 
        user_data: UserCreate, 
        created_by: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Register a new user."""
        try:
            # Check if user already exists
            existing_user = await user_repo.get_by_email(user_data.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )
            
            # Validate password
            password_validation = validate_password(user_data.password)
            if not password_validation["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Password does not meet requirements",
                        "errors": password_validation["errors"]
                    }
                )
            
            # Create user
            hashed_password = get_password_hash(user_data.password)
            
            user = User(
                user_id=user_data.user_id,
                email=user_data.email,
                hashed_password=hashed_password,
                full_name=user_data.full_name,
                role=user_data.role,
                organization=user_data.organization,
                institution_id=user_data.institution_id,
                created_by=created_by
            )
            
            # Save user
            await user_repo.create(user)
            
            # Create audit log
            await DatabaseUtils.create_audit_log(
                user_id=created_by,
                action="REGISTER_USER",
                resource_type="user",
                resource_id=user.user_id,
                details={
                    "email": user.email,
                    "role": user.role,
                    "organization": user.organization
                },
                ip_address=ip_address
            )
            
            logger.info(f"User registered successfully: {user.email}")
            
            return {
                "message": "User registered successfully",
                "user_id": user.user_id,
                "email": user.email
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register user"
            )
    
    async def authenticate_user(
        self, 
        email: str, 
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Authenticate a user and return tokens."""
        try:
            # Rate limiting
            rate_key = f"login:{ip_address or 'unknown'}"
            if not rate_limiter.is_allowed(rate_key, self.login_rate_limit, 60):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts. Please try again later."
                )
            
            # Get user
            user_data = await user_repo.get_by_email(email)
            if not user_data:
                raise AuthenticationError("Invalid email or password")
            
            # Check if account is locked
            if is_account_locked(
                user_data.get("failed_login_attempts", 0),
                user_data.get("locked_until")
            ):
                raise AuthenticationError("Account is temporarily locked due to multiple failed login attempts")
            
            # Check if account is active
            if not user_data.get("is_active", True):
                raise AuthenticationError("Account is deactivated")
            
            # Verify password
            if not verify_password(password, user_data["hashed_password"]):
                # Increment failed attempts
                await self._handle_failed_login(user_data["user_id"], ip_address)
                raise AuthenticationError("Invalid email or password")
            
            # Check 2FA if enabled
            two_factor_required = user_data.get("two_factor_enabled", False)
            
            # Reset failed attempts on successful password verification
            if user_data.get("failed_login_attempts", 0) > 0:
                await user_repo.update(
                    user_data["user_id"],
                    {
                        "failed_login_attempts": 0,
                        "locked_until": None
                    }
                )
            
            # Create tokens
            access_token = create_access_token(
                subject=user_data["user_id"],
                additional_claims={
                    "role": user_data["role"],
                    "email": user_data["email"],
                    "two_factor_verified": not two_factor_required
                }
            )
            
            refresh_token = create_refresh_token(user_data["user_id"])
            
            # Update login info
            await user_repo.update_login_info(user_data["user_id"], ip_address)
            
            # Create audit log
            await DatabaseUtils.create_audit_log(
                user_id=user_data["user_id"],
                action="LOGIN",
                resource_type="user",
                resource_id=user_data["user_id"],
                details={"method": "password"},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(f"User authenticated successfully: {email}")
            
            response = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 3600,  # 1 hour
                "user": UserResponse(**user_data).model_dump(),
                "two_factor_required": two_factor_required
            }
            
            return response
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed"
            )
    
    async def verify_2fa_and_complete_login(
        self,
        user_id: str,
        token: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify 2FA token and complete login process."""
        try:
            user_data = await user_repo.get_by_id(user_id)
            if not user_data:
                raise AuthenticationError("User not found")
            
            if not user_data.get("two_factor_enabled"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="2FA is not enabled for this user"
                )
            
            # Verify 2FA token
            secret = user_data.get("two_factor_secret")
            if not secret or not verify_2fa_token(secret, token):
                raise AuthenticationError("Invalid 2FA token")
            
            # Create new access token with 2FA verified
            access_token = create_access_token(
                subject=user_data["user_id"],
                additional_claims={
                    "role": user_data["role"],
                    "email": user_data["email"],
                    "two_factor_verified": True
                }
            )
            
            # Create audit log
            await DatabaseUtils.create_audit_log(
                user_id=user_data["user_id"],
                action="2FA_VERIFIED",
                resource_type="user",
                resource_id=user_data["user_id"],
                ip_address=ip_address
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 3600,
                "message": "2FA verification successful"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying 2FA: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="2FA verification failed"
            )
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        try:
            # Verify refresh token
            payload = verify_token(refresh_token, "refresh")
            user_id = payload["sub"]
            
            # Get user data
            user_data = await user_repo.get_by_id(user_id)
            if not user_data or not user_data.get("is_active"):
                raise AuthenticationError("User not found or inactive")
            
            # Create new access token
            access_token = create_access_token(
                subject=user_id,
                additional_claims={
                    "role": user_data["role"],
                    "email": user_data["email"],
                    "two_factor_verified": not user_data.get("two_factor_enabled", False)
                }
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 3600
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh failed"
            )
    
    async def setup_2fa(self, user_id: str) -> Dict[str, Any]:
        """Set up 2FA for a user."""
        try:
            user_data = await user_repo.get_by_id(user_id)
            if not user_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Generate 2FA secret
            secret = generate_2fa_secret()
            
            # Update user with 2FA secret (but don't enable yet)
            await user_repo.update(user_id, {"two_factor_secret": secret})
            
            # Generate QR code
            from app.core.security import generate_2fa_qr_code
            qr_code = generate_2fa_qr_code(user_data["email"], secret)
            
            return {
                "secret": secret,
                "qr_code": qr_code,
                "message": "Scan the QR code with your authenticator app and verify with a token to enable 2FA"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error setting up 2FA: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="2FA setup failed"
            )
    
    async def enable_2fa(self, user_id: str, token: str) -> Dict[str, Any]:
        """Enable 2FA after verifying setup token."""
        try:
            user_data = await user_repo.get_by_id(user_id)
            if not user_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            secret = user_data.get("two_factor_secret")
            if not secret:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="2FA setup not initiated. Please setup 2FA first."
                )
            
            # Verify token
            if not verify_2fa_token(secret, token):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid 2FA token"
                )
            
            # Enable 2FA
            await user_repo.update(user_id, {"two_factor_enabled": True})
            
            # Create audit log
            await DatabaseUtils.create_audit_log(
                user_id=user_id,
                action="ENABLE_2FA",
                resource_type="user",
                resource_id=user_id
            )
            
            return {"message": "2FA enabled successfully"}
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error enabling 2FA: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to enable 2FA"
            )
    
    async def disable_2fa(self, user_id: str, password: str) -> Dict[str, Any]:
        """Disable 2FA for a user."""
        try:
            user_data = await user_repo.get_by_id(user_id)
            if not user_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Verify password
            if not verify_password(password, user_data["hashed_password"]):
                raise AuthenticationError("Invalid password")
            
            # Disable 2FA
            await user_repo.update(user_id, {
                "two_factor_enabled": False,
                "two_factor_secret": None
            })
            
            # Create audit log
            await DatabaseUtils.create_audit_log(
                user_id=user_id,
                action="DISABLE_2FA",
                resource_type="user",
                resource_id=user_id
            )
            
            return {"message": "2FA disabled successfully"}
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error disabling 2FA: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to disable 2FA"
            )
    
    async def change_password(
        self, 
        user_id: str, 
        current_password: str, 
        new_password: str
    ) -> Dict[str, Any]:
        """Change user password."""
        try:
            user_data = await user_repo.get_by_id(user_id)
            if not user_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Verify current password
            if not verify_password(current_password, user_data["hashed_password"]):
                raise AuthenticationError("Current password is incorrect")
            
            # Validate new password
            password_validation = validate_password(new_password)
            if not password_validation["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "New password does not meet requirements",
                        "errors": password_validation["errors"]
                    }
                )
            
            # Update password
            new_hashed_password = get_password_hash(new_password)
            await user_repo.update(user_id, {"hashed_password": new_hashed_password})
            
            # Create audit log
            await DatabaseUtils.create_audit_log(
                user_id=user_id,
                action="CHANGE_PASSWORD",
                resource_type="user",
                resource_id=user_id
            )
            
            return {"message": "Password changed successfully"}
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to change password"
            )
    
    async def _handle_failed_login(self, user_id: str, ip_address: Optional[str] = None):
        """Handle failed login attempt."""
        try:
            user_data = await user_repo.get_by_id(user_id)
            if not user_data:
                return
            
            failed_attempts = user_data.get("failed_login_attempts", 0) + 1
            locked_until = calculate_lockout_time(failed_attempts)
            
            await user_repo.update(user_id, {
                "failed_login_attempts": failed_attempts,
                "locked_until": locked_until
            })
            
            # Create audit log
            await DatabaseUtils.create_audit_log(
                user_id=user_id,
                action="FAILED_LOGIN",
                resource_type="user",
                resource_id=user_id,
                details={"failed_attempts": failed_attempts},
                ip_address=ip_address
            )
            
        except Exception as e:
            logger.error(f"Error handling failed login: {str(e)}")

# Global auth service instance
auth_service = AuthService()