from __future__ import annotations


class ServiceError(Exception):
    """Base class for domain errors the API layer maps to HTTP responses."""


class NotFoundError(ServiceError):
    pass


class IllegalStateTransition(ServiceError):
    pass


class UploadValidationError(ServiceError):
    pass


class UploadTooLarge(ServiceError):
    pass
