"""
Custom exceptions for the certificate verification system
"""

class BaseCustomException(Exception):
    """Base exception class for custom exceptions"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class ValidationError(BaseCustomException):
    """Raised when data validation fails"""
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")

class DuplicateError(BaseCustomException):
    """Raised when trying to create a duplicate resource"""
    def __init__(self, message: str):
        super().__init__(message, "DUPLICATE_ERROR")

class NotFoundError(BaseCustomException):
    """Base class for not found errors"""
    def __init__(self, message: str, error_code: str = "NOT_FOUND"):
        super().__init__(message, error_code)

class InstitutionNotFoundError(NotFoundError):
    """Raised when institution is not found"""
    def __init__(self, message: str):
        super().__init__(message, "INSTITUTION_NOT_FOUND")

class CertificateNotFoundError(NotFoundError):
    """Raised when certificate is not found"""
    def __init__(self, message: str):
        super().__init__(message, "CERTIFICATE_NOT_FOUND")

class UserNotFoundError(NotFoundError):
    """Raised when user is not found"""
    def __init__(self, message: str):
        super().__init__(message, "USER_NOT_FOUND")

class UnauthorizedError(BaseCustomException):
    """Raised when user is not authorized to perform an action"""
    def __init__(self, message: str):
        super().__init__(message, "UNAUTHORIZED")

class AuthenticationError(BaseCustomException):
    """Raised when authentication fails"""
    def __init__(self, message: str):
        super().__init__(message, "AUTHENTICATION_ERROR")

class ProcessingError(BaseCustomException):
    """Raised when processing fails"""
    def __init__(self, message: str):
        super().__init__(message, "PROCESSING_ERROR")

class ExternalServiceError(BaseCustomException):
    """Raised when external service call fails"""
    def __init__(self, message: str, service_name: str = None):
        self.service_name = service_name
        super().__init__(message, "EXTERNAL_SERVICE_ERROR")

class ConfigurationError(BaseCustomException):
    """Raised when configuration is invalid"""
    def __init__(self, message: str):
        super().__init__(message, "CONFIGURATION_ERROR")

class RateLimitError(BaseCustomException):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str):
        super().__init__(message, "RATE_LIMIT_ERROR")

class FileProcessingError(BaseCustomException):
    """Raised when file processing fails"""
    def __init__(self, message: str):
        super().__init__(message, "FILE_PROCESSING_ERROR")

class OCRError(BaseCustomException):
    """Raised when OCR processing fails"""
    def __init__(self, message: str):
        super().__init__(message, "OCR_ERROR")

class AIModelError(BaseCustomException):
    """Raised when AI model processing fails"""
    def __init__(self, message: str, model_name: str = None):
        self.model_name = model_name
        super().__init__(message, "AI_MODEL_ERROR")

class DatabaseError(BaseCustomException):
    """Raised when database operation fails"""
    def __init__(self, message: str):
        super().__init__(message, "DATABASE_ERROR")

class SecurityError(BaseCustomException):
    """Raised when security validation fails"""
    def __init__(self, message: str):
        super().__init__(message, "SECURITY_ERROR")