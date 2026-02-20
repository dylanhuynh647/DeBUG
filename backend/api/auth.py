from fastapi import APIRouter, Depends
from backend.dependencies import get_current_user

router = APIRouter()

@router.get("/auth/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current authenticated user information"""
    return user
