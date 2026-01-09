"""
Custom exception handling for the API.
Provides consistent error responses across all API endpoints.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    
    Returns errors in the format:
    {
        "error": "Error message",
        "status_code": 400,
        "details": {...}
    }
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        # Customize the response format
        if isinstance(response.data, dict):
            error_detail = response.data
        else:
            error_detail = {"detail": response.data}
        
        response.data = {
            "error": str(exc),
            "status_code": response.status_code,
            "details": error_detail,
        }
    
    return response
