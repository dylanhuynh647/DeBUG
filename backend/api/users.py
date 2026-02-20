from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from backend.dependencies import get_current_user, role_required, supabase

router = APIRouter()

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

@router.get("/user/me", response_model=UserResponse)
async def get_current_user_profile(user: dict = Depends(get_current_user)):
    """Get current user's profile"""
    user_id = user["user_id"]
    
    result = supabase.table("users").select("*").eq("id", user_id).single().execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    return UserResponse(**result.data)

@router.patch("/user/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    user: dict = Depends(get_current_user)
):
    """Update current user's profile"""
    user_id = user["user_id"]
    
    update_data = {}
    if user_update.full_name is not None:
        update_data["full_name"] = user_update.full_name
    if user_update.avatar_url is not None:
        update_data["avatar_url"] = user_update.avatar_url
    
    update_data["updated_at"] = "now()"
    
    result = supabase.table("users").update(update_data).eq("id", user_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    return UserResponse(**result.data[0])

@router.get("/users")
async def list_all_users(user: dict = Depends(role_required(["admin"]))):
    """List all users (admin only)"""
    result = supabase.table("users").select("*").execute()
    return result.data

@router.get("/users/developers")
async def list_developers_and_admins(current_user: dict = Depends(get_current_user)):
    """List developers and admins (for assignment)"""
    result = supabase.table("users").select("*").in_("role", ["developer", "admin"]).execute()
    return result.data

@router.get("/admin-only")
async def admin_only_endpoint(user: dict = Depends(role_required(["admin"]))):
    """Admin-only endpoint example"""
    return {"message": f"Welcome, Admin {user['email']}! This is admin-only data."}

@router.get("/developer-or-admin")
async def developer_or_admin_endpoint(user: dict = Depends(role_required(["developer", "admin"]))):
    """Developer or Admin endpoint example"""
    return {"message": f"Welcome, {user['role']} {user['email']}! This is developer/admin data."}
