from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException, AuthenticationFailed, NotAuthenticated, PermissionDenied
from rest_framework import status
from .utils import custom_response
from .error_messages import AUTH_ERROR_MESSAGES

def custom_exception_handler(exc, context):
    """
    Custom exception handler that formats DRF's default error responses
    to match our standard response format.
    """
    # First call DRF's default exception handler to get the standard error response
    response = exception_handler(exc, context)
    
    if response is not None:
        status_code = response.status_code
        
        # Customize error messages for authentication-related exceptions
        if isinstance(exc, NotAuthenticated):
            detail = AUTH_ERROR_MESSAGES['not_authenticated']
        elif isinstance(exc, AuthenticationFailed):
            detail = AUTH_ERROR_MESSAGES['authentication_failed']
        elif isinstance(exc, PermissionDenied):
            detail = AUTH_ERROR_MESSAGES['permission_denied']
        # Extract the error detail from response
        elif isinstance(response.data, dict):
            if 'detail' in response.data:
                detail = response.data['detail']
            else:
                # For validation errors and other nested errors
                detail = response.data
        else:
            detail = response.data
            
        # Format the response using our custom_response function
        custom_resp = custom_response(
            detail=detail,
            status_code=status_code,
            success=False
        )
        
        return custom_resp
    
    # If no standard DRF response was generated, return None
    # Django will return a 500 error response
    return None 