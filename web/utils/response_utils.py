from rest_framework.response import Response
from rest_framework import status

def custom_response(data=None, detail=None, status_code=status.HTTP_200_OK, success=True):
    """
    Create a standardized response format for all API endpoints
    
    Parameters:
    - data: The result payload to return (default: None)
    - detail: Error message or detail information (default: None)
    - status_code: HTTP status code (default: 200)
    - success: Boolean indicating if the request was successful (default: True)
    
    Returns:
    - Response object with standardized format
    """
    if success and status_code >= 400:
        success = False
    elif not success and status_code < 400:
        status_code = status.HTTP_400_BAD_REQUEST
    
    response_data = {
        'status': status_code,
        'success': success,
        'result': data,
        'detail': detail
    }
    
    return Response(response_data, status=status_code) 