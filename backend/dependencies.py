from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from jose import JWTError, jwt
import os
from typing import Optional
from uuid import UUID

security = HTTPBearer()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Missing Supabase environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Export supabase for use in other modules
__all__ = ["supabase", "supabase_auth_secure", "role_required", "get_current_user"]

async def supabase_auth_secure(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Verify Supabase JWT and return user info"""
    token = credentials.credentials
    
    import logging
    logger = logging.getLogger(__name__)
    try:
        # Verify token with Supabase
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        user_id = user_response.user.id
        
        # Get user role from public.users table
        logger.warning(f"About to select user from users table: id={user_id}")
        try:
            user_data = supabase.table("users").select("role").eq("id", user_id).single().execute()
            logger.warning(f"user_data returned from select: {user_data}")
            logger.warning(f"user_data.status_code: {getattr(user_data, 'status_code', None)}")
        except Exception as select_first_exc:
            logger.error(f"Initial select failed: {select_first_exc}")
            user_data = None

        # Always attempt insert and log the result
        logger.warning(f"Attempting forced insert: id={user_id}, email={user_response.user.email}")
        try:
            insert_response = supabase.table("users").insert({
                "id": str(user_id),
                "email": user_response.user.email,
                "role": "reporter"
            }).execute()
            logger.warning(f"Forced insert response: {insert_response}")
        except Exception as insert_exc:
            logger.error(f"Forced user insert failed: {insert_exc}")

        # Try fetching again after insert
        try:
            user_data = supabase.table("users").select("role").eq("id", user_id).single().execute()
            logger.warning(f"Post-insert select response: {user_data}")
        except Exception as select_exc:
            logger.error(f"Post-insert select failed: {select_exc}")
        user_role = user_data.data.get("role", "reporter") if user_data.data else "reporter"
        return {
            "user_id": user_id,
            "email": user_response.user.email,
            "role": user_role
        }
    except Exception as e:
        # Don't expose internal error details
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

def role_required(allowed_roles: list[str]):
    """Dependency factory for role-based access control"""
    def _role_checker(user: dict = Depends(supabase_auth_secure)):
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User with role '{user['role']}' does not have permission. Required roles: {', '.join(allowed_roles)}"
            )
        return user
    return _role_checker

def get_current_user(user: dict = Depends(supabase_auth_secure)) -> dict:
    """Get current authenticated user"""
    return user
