"""
JWT Authentication Middleware

Note: The JWTCookieMiddleware class has been removed as the application
now uses token-based authentication instead of cookie-based authentication.

Authentication is now handled by the CustomJWTAuthentication class,
which looks for JWT tokens in the Authorization header.
""" 