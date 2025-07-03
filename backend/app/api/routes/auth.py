"""
Authentication endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import jwt
from passlib.context import CryptContext

from app.core.database import get_async_session
from app.core.config import get_settings
from app.schemas.base import SuccessResponse, ErrorResponse

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthSchemas:
    """Authentication request/response schemas."""
    
    class LoginRequest:
        def __init__(self, email: str, password: str):
            self.email = email
            self.password = password
    
    class TokenResponse:
        def __init__(self, access_token: str, token_type: str = "bearer", expires_in: int = 3600):
            self.access_token = access_token
            self.token_type = token_type
            self.expires_in = expires_in
    
    class UserInfo:
        def __init__(self, id: str, email: str, role: str, permissions: list):
            self.id = id
            self.email = email
            self.role = role
            self.permissions = permissions


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    settings = get_settings()
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and extract user info."""
    try:
        settings = get_settings()
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


@router.post("/login")
async def login(
    email: str,
    password: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Authenticate user and return access token.
    
    For MVP, this is a simple implementation.
    In production, integrate with proper user management system.
    """
    try:
        # For MVP - simple demo authentication
        # In production, verify against user database with proper password hashing
        
        if email == "demo@scanzakup.kz" and password == "demo2024":
            # Create demo token
            access_token = create_access_token(
                data={
                    "sub": "demo-user-1",
                    "email": email,
                    "role": "analyst",
                    "permissions": ["read:procurements", "read:analytics", "export:data"]
                }
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 86400,  # 24 hours
                "user": {
                    "id": "demo-user-1",
                    "email": email,
                    "role": "analyst",
                    "permissions": ["read:procurements", "read:analytics", "export:data"]
                }
            }
        
        elif email == "admin@scanzakup.kz" and password == "admin2024":
            # Create admin token
            access_token = create_access_token(
                data={
                    "sub": "admin-user-1", 
                    "email": email,
                    "role": "admin",
                    "permissions": ["read:*", "write:*", "admin:*"]
                }
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer", 
                "expires_in": 86400,
                "user": {
                    "id": "admin-user-1",
                    "email": email,
                    "role": "admin",
                    "permissions": ["read:*", "write:*", "admin:*"]
                }
            }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


@router.post("/refresh")
async def refresh_token(
    current_user: dict = Depends(verify_token)
):
    """
    Refresh access token.
    """
    try:
        # Create new token with same user data
        access_token = create_access_token(
            data={
                "sub": current_user["sub"],
                "email": current_user["email"], 
                "role": current_user["role"],
                "permissions": current_user["permissions"]
            }
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 86400
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.get("/me")
async def get_current_user(
    current_user: dict = Depends(verify_token)
):
    """
    Get current user information.
    """
    return {
        "id": current_user["sub"],
        "email": current_user["email"],
        "role": current_user["role"],
        "permissions": current_user["permissions"]
    }


@router.post("/logout")
async def logout(
    current_user: dict = Depends(verify_token)
):
    """
    Logout user (invalidate token).
    
    For JWT tokens, client should discard the token.
    In production, maintain a blacklist of revoked tokens.
    """
    # In production, add token to blacklist/revocation list
    return SuccessResponse(
        message="Successfully logged out",
        data={"user_id": current_user["sub"]}
    )


@router.get("/permissions")
async def get_user_permissions(
    current_user: dict = Depends(verify_token)
):
    """
    Get user permissions and access levels.
    """
    return {
        "user_id": current_user["sub"],
        "role": current_user["role"],
        "permissions": current_user["permissions"],
        "access_level": "read" if "read:*" not in current_user["permissions"] else "full"
    }


# Helper function for route protection
def require_permission(permission: str):
    """Dependency to require specific permission."""
    def permission_checker(current_user: dict = Depends(verify_token)):
        user_permissions = current_user.get("permissions", [])
        
        # Check for wildcard permissions
        if "admin:*" in user_permissions or f"{permission.split(':')[0]}:*" in user_permissions:
            return current_user
            
        # Check for specific permission
        if permission in user_permissions:
            return current_user
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {permission}"
        )
    
    return permission_checker


# Optional user dependency (for endpoints that work with/without auth)
def optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    """Get user info if authenticated, None otherwise."""
    if not credentials:
        return None
    
    try:
        settings = get_settings()
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        return None 