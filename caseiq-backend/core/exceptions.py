from rest_framework.views import exception_handler
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that provides consistent error responses.
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        response.data = {
            "error": True,
            "status_code": response.status_code,
            "detail": response.data,
        }
    else:
        # Log unhandled exceptions
        logger.exception("Unhandled exception: %s", exc)
        response = Response(
            {
                "error": True,
                "status_code": 500,
                "detail": "Internal server error. Please try again later.",
            },
            status=500,
        )
    
    return response