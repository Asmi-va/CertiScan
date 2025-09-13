
from datetime import datetime, timedelta
from typing import Any, Optional, Union, Dict, List
import secrets
import pyotp
import qrcode
from io import BytesIO
import base64

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.db.models import UserRole, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Password validation settings
MIN_PASSWORD_LENGTH = 8
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_NUMBERS = True
REQUIRE_SPECIAL_CHARS = True

class SecurityException(HTTPException):
    """Custom security exception."""
    pass

class AuthenticationError(SecurityException):
    """Authentication failed."""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class AuthorizationError(SecurityException):
    """Authorization failed."""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class TokenExpiredError(SecurityException):
    """Token has expired."""
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

# Password utilities
def validate_password(password: str) -> Dict[str, Any]:
    """Validate password strength and return validation result."""
    errors = []
    
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
    
    if REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    
    if REQUIRE_SPECIAL_CHARS and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "strength": calculate_password_strength(password)
    }

def calculate_password_strength(password: str) -> str:
    """Calculate password strength score."""
    score = 0
    
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 1
    
    if score <= 2:
        return "weak"
    elif score <= 4:
        return "medium"
    else:
        return "strong"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)

# JWT Token utilities
def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "iat": datetime.utcnow()
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any]) -> str:
    """Create a JWT refresh token."""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check token type
        if payload.get("type") != token_type:
            raise AuthenticationError("Invalid token type")
        
        # Check expiration
        exp = payload.get("exp")
        if exp is None:
            raise AuthenticationError("Token missing expiration")
        
        if datetime.utcnow() > datetime.fromtimestamp(exp):
            raise TokenExpiredError("Token has expired")
        
        return payload
    
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode token without verification (for debugging)."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

# Two-Factor Authentication utilities
def generate_2fa_secret() -> str:
    """Generate a new 2FA secret key."""
    return pyotp.random_base32()

def generate_2fa_qr_code(user_email: str, secret: str, issuer: str = "Certificate Verification System") -> str:
    """Generate QR code for 2FA setup."""
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user_email,
        issuer_name=issuer
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 string
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"

def verify_2fa_token(secret: str, token: str) -> bool:
    """Verify a 2FA token."""
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)  # Allow 1 window tolerance

# Session and security utilities
def generate_session_id() -> str:
    """Generate a secure session ID."""
    return secrets.token_urlsafe(32)

def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)

# Role-based permissions
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        "read:all", "write:all", "delete:all",
        "manage:users", "manage:institutions", "manage:blacklist",
        "view:analytics", "manage:system"
    ],
    UserRole.INSTITUTION: [
        "read:own_certificates", "write:own_certificates",
        "read:own_institution", "write:own_institution",
        "manage:own_users", "upload:certificates"
    ],
    UserRole.EMPLOYER: [
        "read:certificates", "verify:certificates",
        "read:verification_history", "request:verification"
    ],
    UserRole.GOVERNMENT: [
        "read:all_certificates", "verify:certificates",
        "read:analytics", "read:blacklist", "write:blacklist",
        "read:institutions", "audit:system"
    ],
    UserRole.STUDENT: [
        "read:own_certificates", "verify:own_certificates",
        "share:own_certificates"
    ]
}

def get_user_permissions(role: UserRole) -> List[str]:
    """Get permissions for a user role."""
    return ROLE_PERMISSIONS.get(role, [])

def check_permission(user_role: UserRole, required_permission: str) -> bool:
    """Check if a user role has a specific permission."""
    user_permissions = get_user_permissions(user_role)
    
    # Check for exact match
    if required_permission in user_permissions:
        return True
    
    # Check for wildcard permissions
    for permission in user_permissions:
        if permission.endswith(":all"):
            permission_type = permission.split(":")[0]
            required_type = required_permission.split(":")[0]
            if permission_type == required_type:
                return True
    
    return False

# Rate limiting utilities
class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed under rate limit."""
        now = datetime.utcnow()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if (now - req_time).total_seconds() < window_seconds
        ]
        
        # Check if under limit
        if len(self.requests[key]) < max_requests:
            self.requests[key].append(now)
            return True
        
        return False

# Global rate limiter instance
rate_limiter = RateLimiter()

# Account security utilities
def is_account_locked(failed_attempts: int, locked_until: Optional[datetime]) -> bool:
    """Check if account is locked due to failed login attempts."""
    if locked_until and datetime.utcnow() < locked_until:
        return True
    
    # Progressive lockout: 3 attempts = 15 min, 5 attempts = 1 hour, 10+ attempts = 24 hours
    if failed_attempts >= 10:
        return True  # Should be handled by locked_until, but safety check
    
    return False

def calculate_lockout_time(failed_attempts: int) -> Optional[datetime]:
    """Calculate account lockout time based on failed attempts."""
    if failed_attempts >= 10:
        return datetime.utcnow() + timedelta(hours=24)
    elif failed_attempts >= 5:
        return datetime.utcnow() + timedelta(hours=1)
    elif failed_attempts >= 3:
        return datetime.utcnow() + timedelta(minutes=15)

    return None

# User authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user from JWT token."""
    try:
        token = credentials.credentials
        payload = verify_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise AuthenticationError("Invalid token payload")

        # TODO: Fetch user from database
        # For now, return a mock user based on token payload
        user = User(
            user_id=user_id,
            email=payload.get("email", "mock@example.com"),
            hashed_password="",  # Not needed for current user
            full_name=payload.get("full_name", "Mock User"),
            role=payload.get("role", UserRole.ADMIN),
            is_active=True,
            is_verified=True
        )

        return user

    except JWTError as e:
        raise AuthenticationError(f"Token validation failed: {str(e)}")
    except Exception as e:
        raise AuthenticationError(f"Authentication failed: {str(e)}")
