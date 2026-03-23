from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.dependencies import get_current_user, ensure_project_role, get_project_role, supabase
from backend.schemas.project import (
    ProjectCreate,
    ProjectMemberAdd,
    ProjectMemberResponse,
    ProjectMemberUpdate,
    ProjectResponse,
)

router = APIRouter()


def _normalize_project_row(row: dict, my_role: str) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row.get("description"),
        "owner_id": row["owner_id"],
        "my_role": my_role,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.get("/projects", response_model=List[ProjectResponse])
async def list_my_projects(user: dict = Depends(get_current_user)):
    user_id = str(user["user_id"])
    memberships_result = (
        supabase.table("project_members")
        .select("project_id,role")
        .eq("user_id", user_id)
        .execute()
    )

    memberships = memberships_result.data or []
    if not memberships:
        return []

    project_ids = [membership["project_id"] for membership in memberships]
    projects_result = (
        supabase.table("projects")
        .select("id,name,description,owner_id,created_at,updated_at")
        .in_("id", project_ids)
        .order("created_at", desc=True)
        .execute()
    )

    role_by_project_id = {item["project_id"]: item["role"] for item in memberships}
    return [
        _normalize_project_row(project, role_by_project_id.get(project["id"], "reporter"))
        for project in (projects_result.data or [])
    ]


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, user: dict = Depends(get_current_user)):
    user_id = str(user["user_id"])

    created_result = (
        supabase.table("projects")
        .insert({
            "name": payload.name,
            "description": payload.description,
            "owner_id": user_id,
        })
        .execute()
    )

    if not created_result.data:
        raise HTTPException(status_code=500, detail="Failed to create project")

    project = created_result.data[0]

    supabase.table("project_members").upsert(
        {
            "project_id": project["id"],
            "user_id": user_id,
            "role": "owner",
            "added_by": user_id,
        }
    ).execute()

    return ProjectResponse(**_normalize_project_row(project, "owner"))


@router.get("/projects/{project_id}/members", response_model=List[ProjectMemberResponse])
async def list_project_members(
    project_id: UUID,
    q: Optional[str] = Query(default=None, max_length=255),
    user: dict = Depends(get_current_user),
):
    ensure_project_role(supabase, project_id, user["user_id"], ["owner", "admin", "developer", "reporter"])

    members_result = (
        supabase.table("project_members")
        .select("user_id,role,created_at,updated_at")
        .eq("project_id", str(project_id))
        .execute()
    )
    members = members_result.data or []
    if not members:
        return []

    user_ids = [member["user_id"] for member in members]
    users_result = (
        supabase.table("users")
        .select("id,email,full_name,avatar_url")
        .in_("id", user_ids)
        .execute()
    )

    users_by_id = {row["id"]: row for row in (users_result.data or [])}
    query_text = q.strip().lower() if q else None

    response_rows = []
    for member in members:
        profile = users_by_id.get(member["user_id"], {})
        email = profile.get("email")
        full_name = profile.get("full_name")
        if query_text:
            haystacks = [
                (email or "").lower(),
                (full_name or "").lower(),
            ]
            if not any(query_text in value for value in haystacks):
                continue

        response_rows.append(
            {
                "user_id": member["user_id"],
                "role": member["role"],
                "email": email,
                "full_name": full_name,
                "avatar_url": profile.get("avatar_url"),
                "created_at": member["created_at"],
                "updated_at": member["updated_at"],
            }
        )

    return response_rows


@router.get("/projects/{project_id}/users/search")
async def search_users_for_project(
    project_id: UUID,
    q: str = Query(..., min_length=1, max_length=255),
    user: dict = Depends(get_current_user),
):
    ensure_project_role(supabase, project_id, user["user_id"], ["owner"])

    query_text = q.strip().lower()
    users_result = supabase.table("users").select("id,email,full_name,avatar_url").execute()
    project_members_result = (
        supabase.table("project_members")
        .select("user_id")
        .eq("project_id", str(project_id))
        .execute()
    )
    existing_members = {member["user_id"] for member in (project_members_result.data or [])}

    filtered = []
    for row in (users_result.data or []):
        haystacks = [
            (row.get("email") or "").lower(),
            (row.get("full_name") or "").lower(),
        ]
        if any(query_text in value for value in haystacks):
            filtered.append(
                {
                    "id": row["id"],
                    "email": row.get("email"),
                    "full_name": row.get("full_name"),
                    "avatar_url": row.get("avatar_url"),
                    "is_member": row["id"] in existing_members,
                }
            )

    return filtered[:20]


@router.post("/projects/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: UUID,
    payload: ProjectMemberAdd,
    user: dict = Depends(get_current_user),
):
    ensure_project_role(supabase, project_id, user["user_id"], ["owner"])

    target_user_result = (
        supabase.table("users")
        .select("id,email,full_name,avatar_url")
        .eq("id", str(payload.user_id))
        .single()
        .execute()
    )
    if not target_user_result.data:
        raise HTTPException(status_code=404, detail="User not found")

    existing_member = get_project_role(supabase, project_id, payload.user_id)
    if existing_member:
        raise HTTPException(status_code=400, detail="User is already a member of this project")

    member_result = (
        supabase.table("project_members")
        .insert(
            {
                "project_id": str(project_id),
                "user_id": str(payload.user_id),
                "role": payload.role,
                "added_by": str(user["user_id"]),
            }
        )
        .execute()
    )

    if not member_result.data:
        raise HTTPException(status_code=500, detail="Failed to add member")

    member = member_result.data[0]
    profile = target_user_result.data
    return {
        "user_id": member["user_id"],
        "role": member["role"],
        "email": profile.get("email"),
        "full_name": profile.get("full_name"),
        "avatar_url": profile.get("avatar_url"),
        "created_at": member["created_at"],
        "updated_at": member["updated_at"],
    }


@router.patch("/projects/{project_id}/members/{member_user_id}", response_model=ProjectMemberResponse)
async def update_project_member_role(
    project_id: UUID,
    member_user_id: UUID,
    payload: ProjectMemberUpdate,
    user: dict = Depends(get_current_user),
):
    ensure_project_role(supabase, project_id, user["user_id"], ["owner"])

    current_role = get_project_role(supabase, project_id, member_user_id)
    if not current_role:
        raise HTTPException(status_code=404, detail="Project member not found")
    if current_role == "owner":
        raise HTTPException(status_code=400, detail="Owner role cannot be changed")

    update_result = (
        supabase.table("project_members")
        .update({"role": payload.role})
        .eq("project_id", str(project_id))
        .eq("user_id", str(member_user_id))
        .execute()
    )

    if not update_result.data:
        raise HTTPException(status_code=500, detail="Failed to update member role")

    profile_result = (
        supabase.table("users")
        .select("id,email,full_name,avatar_url")
        .eq("id", str(member_user_id))
        .single()
        .execute()
    )

    updated_member = update_result.data[0]
    profile = profile_result.data or {}
    return {
        "user_id": updated_member["user_id"],
        "role": updated_member["role"],
        "email": profile.get("email"),
        "full_name": profile.get("full_name"),
        "avatar_url": profile.get("avatar_url"),
        "created_at": updated_member["created_at"],
        "updated_at": updated_member["updated_at"],
    }
