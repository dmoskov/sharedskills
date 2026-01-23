#!/usr/bin/env python3
"""
Asana SDK Exception Classes

Custom exception hierarchy for Asana API errors.
"""

from typing import Optional


class AsanaClientError(Exception):
    """Base exception for Asana client errors"""

    pass


class AsanaAuthenticationError(AsanaClientError):
    """Raised when authentication fails (401)"""

    pass


class AsanaRateLimitError(AsanaClientError):
    """Raised when rate limit is exceeded (429)"""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class AsanaNotFoundError(AsanaClientError):
    """Raised when resource is not found (404)"""

    pass


class AsanaValidationError(AsanaClientError):
    """Raised when request parameters are invalid (400)"""

    pass


class AsanaServerError(AsanaClientError):
    """Raised when server returns 5xx error"""

    pass
