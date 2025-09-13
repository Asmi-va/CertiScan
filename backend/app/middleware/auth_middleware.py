"""
Authentication and authorization middleware.
"""
from typing import Optional, List, Callable
from functools import wraps
import logging

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import (
    verify_token, check_permission, AuthenticationError, AuthorizationError
)
from app.db.models import UserRole
from app.db.utils import user_repo

logger = logging.getLogger(__name__)
security = HTTPBearer()

class AuthMiddleware:
    """Authentication and authorization middleware."""
    
    @staticmethod
    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> dict:
        """Get current authenticated user from JWT token."""
        try:
            # Verify token
            payload = verify_token(credentials.credentials, "access")
            user_id = payload["sub"]
            
            # Get user data
            user_data = await user_repo.get_by_id(user_id)
            if not user_data:
                raise AuthenticationError("User not found")
            
            if not user_data.get("is_active", True):
                raise AuthenticationError("User account is deactivated")
            
            # Add token claims to user data
            user_data["token_claims"] = payload
            
            return user_data
        
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error getting current user: {str(e)}")
            raise AuthenticationError("Invalid authentication credentials")
    
    @staticmethod
    async def get_current_active_user(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        """Get current active user (alias for get_current_user)."""
        return current_user
    
    @staticmethod
    async def get_current_admin_user(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        """Get current user if they are an admin."""
        if current_user["role"] != UserRole.ADMIN:
            raise AuthorizationError("Admin access required")
        return current_user
    
    @staticmethod
    async def get_current_institution_user(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        """Get current user if they are an institution user."""
        if current_user["role"] != UserRole.INSTITUTION:
            raise AuthorizationError("Institution access required")
        return current_user
    
    @staticmethod
    async def get_current_government_user(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        """Get current user if they are a government user."""
        if current_user["role"] != UserRole.GOVERNMENT:
            raise AuthorizationError("Government access required")
        return current_user
    
    @staticmethod
    def require_permissions(required_permissions: List[str]):
        """Dependency factory for requiring specific permissions."""
        async def permission_checker(
            current_user: dict = Depends(AuthMiddleware.get_current_user)
        ) -> dict:
            user_role = UserRole(current_user["role"])
            
            # Check each required permission
            for permission in required_permissions:
                if not check_permission(user_role, permission):
                    raise AuthorizationError(
                        f"Insufficient permissions. Required: {', '.join(required_permissions)}"
                    )
            
            return current_user
        
        return permission_checker
    
    @staticmethod
    def require_2fa_verification():
        """Dependency for requiring 2FA verification."""
        async def two_factor_checker(
            current_user: dict = Depends(AuthMiddleware.get_current_user)
        ) -> dict:
            token_claims = current_user.get("token_claims", {})
            
            # Check if 2FA is enabled for user
            if current_user.get("two_factor_enabled", False):
                # Check if 2FA was verified in this session
                if not token_claims.get("two_factor_verified", False):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Two-factor authentication required"
                    )
            
            return current_user
        
        return two_factor_checker
    
    @staticmethod
    def require_institution_access(institution_id: Optional[str] = None):
        """Dependency factory for requiring access to specific institution."""
        async def institution_checker(
            current_user: dict = Depends(AuthMiddleware.get_current_user)
        ) -> dict:
            user_role = UserRole(current_user["role"])
            
            # Admins and government users have access to all institutions
            if user_role in [UserRole.ADMIN, UserRole.GOVERNMENT]:
                return current_user
            
            # Institution users can only access their own institution
            if user_role == UserRole.INSTITUTION:
                user_institution_id = current_user.get("institution_id")
                if institution_id and user_institution_id != institution_id:
                    raise AuthorizationError("Access denied to this institution")
                return current_user
            
            # Other roles don't have institution access
            raise AuthorizationError("Institution access required")
        
        return institution_checker

# Create middleware instance
auth_middleware = AuthMiddleware()

# Common dependency shortcuts
get_current_user = auth_middleware.get_current_user
get_current_active_user = auth_middleware.get_current_active_user
get_current_admin_user = auth_middleware.get_current_admin_user
get_current_institution_user = auth_middleware.get_current_institution_user
get_current_government_user = auth_middleware.get_current_government_user

# Permission-based dependencies
require_read_certificates = auth_middleware.require_permissions(["read:certificates"])
require_write_certificates = auth_middleware.require_permissions(["write:certificates"])
require_manage_users = auth_middleware.require_permissions(["manage:users"])
require_manage_blacklist = auth_middleware.require_permissions(["manage:blacklist"])
require_view_analytics = auth_middleware.require_permissions(["view:analytics"])
require_system_admin = auth_middleware.require_permissions(["manage:system"])

# 2FA requirement
require_2fa = auth_middleware.require_2fa_verification()

# Decorators for route protection
def require_auth(func):
    """Decorator to require authentication for a route."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # This decorator is mainly for documentation
        # Actual auth is handled by FastAPI dependencies
        return await func(*args, **kwargs)
    return wrapper

def require_role(allowed_roles: List[UserRole]):
    """Decorator to require specific roles for a route."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This decorator is mainly for documentation
            # Actual role checking is handled by FastAPI dependencies
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Request context utilities
async def get_request_context(request: Request) -> dict:
    """Extract request context for logging and audit."""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers)
    }

# Rate limiting middleware
class RateLimitMiddleware:
    """Rate limiting middleware for API endpoints."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
    
    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting."""
        from app.core.security import rate_limiter
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check rate limit
        if not rate_limiter.is_allowed(
            f"api:{client_ip}", 
            self.requests_per_minute, 
            60
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Process request
        response = await call_next(request)
        return response

# Security headers middleware
async def add_security_headers(request: Request, call_next):
    """Add security headers to responses."""
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response