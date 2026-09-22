class BackendAPIError(Exception):
    """Base exception for Backend API errors."""
    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class AuthenticationError(BackendAPIError):
    """Raised when authentication fails (401)."""
    pass

class PermissionDeniedError(BackendAPIError):
    """Raised when role does not have permission (403)."""
    pass

class NotFoundError(BackendAPIError):
    """Raised when resource is not found (404)."""
    pass

class ValidationError(BackendAPIError):
    """Raised when input validation fails (422)."""
    pass

class BackendUnavailableError(BackendAPIError):
    """Raised when backend server is unreachable or offline."""
    pass
