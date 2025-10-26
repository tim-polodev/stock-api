from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import httpx
import os
from typing import Optional, Dict, Any

AUTH_API_URL = os.getenv("AUTH_API_URL", "https://auth.polodev.com")


async def validate_token_middleware(request: Request, call_next):
    """
    Middleware to validate JWT tokens for protected routes.
    Skips validatt sion for docs and openapi endpoints.
    """
    # Skip token validation for docs and openapi endpoints
    if request.url.path in ["/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)

    # Get the Authorization header
    auth_header = request.headers.get("Authorization")
    print("[Tim debug] auth_header", auth_header)

    if not auth_header:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authorization header missing"}
        )

    try:
        # Call the authentication service to validate the token
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{AUTH_API_URL}/api/auth/validateToken",
                headers={"Authorization": auth_header},
                timeout=10.0
            )

            if response.status_code != 200:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid or expired token"}
                )

            # Parse the validation response
            validation_data = response.json()

            if not validation_data.get("valid", False):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Token validation failed"}
                )

            # Attach user info to request state for use in route handlers
            request.state.user = validation_data.get("user")

    except httpx.TimeoutException:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Authentication service timeout"}
        )
    except httpx.RequestError as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": f"Authentication service error: {str(e)}"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Internal server error: {str(e)}"}
        )

    # Proceed to the route handler
    response = await call_next(request)
    return response


async def validate_token(authorization: str) -> Dict[str, Any]:
    """
    Helper function to validate a token by calling the authentication service.
    Can be used as a dependency in specific routes.
    
    Args:
        authorization: The Authorization header value (e.g., "Bearer <token>")
    
    Returns:
        Dict containing user information if valid
    
    Raises:
        HTTPException: If token is invalid or service is unavailable
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{AUTH_API_URL}/api/auth/validateToken",
                headers={"Authorization": authorization},
                timeout=10.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token"
                )

            validation_data = response.json()

            if not validation_data.get("valid", False):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token validation failed"
                )

            return validation_data.get("user")

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service timeout"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication service error: {str(e)}"
        )


def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Dependency to get the current authenticated user from request state.
    Use this in route handlers after the middleware has run.
    
    Example:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"message": f"Hello {user['email']}"}
    """
    if not hasattr(request.state, "user") or request.state.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return request.state.user
