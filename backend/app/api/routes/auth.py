"""
Authentication endpoints and utilities.
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
security = HTTPBearer(auto_error=False)
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


def optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    """
    Optional authentication dependency.
    Returns user info if valid token provided, None otherwise.
    """
    if not credentials:
        return None
    
    # For MVP - simple mock validation
    if credentials.credentials == "valid_token":
        return {
            "id": 1,
            "email": "admin@scanzakup.kz",
            "role": "admin",
            "name": "Администратор",
            "is_active": True
        }
    
    return None


@router.post("/login", response_model=dict)
async def login(credentials: dict):
    """
    User login endpoint.
    For MVP - returns mock token for demo purposes.
    """
    email = credentials.get("email")
    password = credentials.get("password")
    
    # Mock validation
    if email == "admin@scanzakup.kz" and password == "admin":
        return {
            "access_token": "valid_token",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": 1,
                "email": "admin@scanzakup.kz",
                "role": "admin",
                "name": "Администратор"
            }
        }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


@router.post("/logout", response_model=dict)
async def logout(current_user: Optional[dict] = Depends(optional_user)):
    """
    User logout endpoint.
    """
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=dict)
async def get_current_user(current_user: Optional[dict] = Depends(optional_user)):
    """
    Get current user information.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    return current_user


@router.get("/status", response_model=dict)
async def auth_status():
    """
    Check authentication system status.
    """
    return {
        "status": "operational",
        "version": "1.0.0",
        "auth_enabled": True,
        "timestamp": datetime.now()
    }


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