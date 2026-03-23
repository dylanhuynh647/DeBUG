from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from uuid import UUID
from typing import Optional, List
from datetime import datetime
from backend.dependencies import get_current_user, ensure_project_role, get_project_role, supabase
from backend.schemas.bug import BugCreate, BugUpdate, BugResponse, BugSeverityUpdate
from backend.crud import bug
from backend.utils.audit_log import log_bug_created, log_bug_updated, log_bug_status_changed, log_bug_fixed, get_client_ip
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/bugs", response_model=BugResponse, status_code=status.HTTP_201_CREATED)
async def create_bug(
    request: Request,
    bug_data: BugCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new bug"""
    try:
        ensure_project_role(
            supabase,
            bug_data.project_id,
            user["user_id"],
            ["owner", "admin", "developer", "reporter"],
        )
        if bug_data.assigned_to and not get_project_role(supabase, bug_data.project_id, bug_data.assigned_to):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not a member of this project"
            )
        created = bug.create_bug(supabase, bug_data, UUID(user["user_id"]))
        # Fetch with artifacts
        full_bug = bug.get_bug(supabase, UUID(created["id"]), bug_data.project_id)
        
        # Audit logging
        log_bug_created(UUID(created["id"]), user["user_id"], get_client_ip(request))
        
        return BugResponse(**full_bug)
    except HTTPException:
        raise
    except ValueError as e:
        # Validation errors - don't expose internal details
        logger.warning(f"Validation error creating bug: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data"
        )
    except Exception as e:
        logger.error(f"Error creating bug: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bug"
        )

@router.get("/bugs", response_model=List[BugResponse])
async def list_bugs(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    bug_status: Optional[List[str]] = Query(None, alias="status"),
    bug_type: Optional[List[str]] = Query(None),
    reporter_id: Optional[UUID] = Query(None),
    assigned_to: Optional[UUID] = Query(None),
    artifact_type: Optional[List[str]] = Query(None),
    found_at_from: Optional[datetime] = Query(None),
    found_at_to: Optional[datetime] = Query(None),
    user: dict = Depends(get_current_user)
):
    """List all bugs with filtering"""
    try:
        ensure_project_role(
            supabase,
            project_id,
            user["user_id"],
            ["owner", "admin", "developer", "reporter"],
        )
        bugs_list = bug.get_bugs(
            supabase,
            project_id=project_id,
            skip=skip,
            limit=limit,
            status=bug_status,
            bug_type=bug_type,
            reporter_id=reporter_id,
            assigned_to=assigned_to,
            artifact_type=artifact_type,
            found_at_from=found_at_from,
            found_at_to=found_at_to
        )
        return [BugResponse(**b) for b in bugs_list]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list bugs"
        )

@router.get("/bugs/{bug_id}", response_model=BugResponse)
async def get_bug(
    bug_id: UUID,
    project_id: UUID,
    user: dict = Depends(get_current_user)
):
    """Get a single bug by ID"""
    try:
        ensure_project_role(
            supabase,
            project_id,
            user["user_id"],
            ["owner", "admin", "developer", "reporter"],
        )
        bug_data = bug.get_bug(supabase, bug_id, project_id)
        if not bug_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bug not found"
            )
        return BugResponse(**bug_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.patch("/bugs/{bug_id}", response_model=BugResponse)
async def update_bug(
    request: Request,
    bug_id: UUID,
    project_id: UUID,
    bug_data: BugUpdate,
    user: dict = Depends(get_current_user)
):
    """Update a bug (developer or admin only)"""
    try:
        ensure_project_role(
            supabase,
            project_id,
            user["user_id"],
            ["owner", "admin", "developer"],
        )
        if bug_data.assigned_to and not get_project_role(supabase, project_id, bug_data.assigned_to):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not a member of this project"
            )
        # Get current bug to track status changes
        current_bug = bug.get_bug(supabase, bug_id, project_id)
        if not current_bug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bug not found"
            )
        
        old_status = current_bug.get("status")
        
        updated = bug.update_bug(supabase, bug_id, bug_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bug not found"
            )
        
        # Fetch with artifacts
        full_bug = bug.get_bug(supabase, bug_id, project_id)
        
        # Audit logging
        changes = {}
        if bug_data.title is not None:
            changes["title"] = bug_data.title
        if bug_data.description is not None:
            changes["description"] = bug_data.description
        if bug_data.severity is not None:
            changes["severity"] = bug_data.severity
        if bug_data.status is not None and bug_data.status != old_status:
            log_bug_status_changed(bug_id, user["user_id"], old_status, bug_data.status, get_client_ip(request))
            if bug_data.status == "resolved":
                log_bug_fixed(bug_id, user["user_id"], get_client_ip(request))
        if changes:
            log_bug_updated(bug_id, user["user_id"], changes, get_client_ip(request))
        
        return BugResponse(**full_bug)
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error updating bug: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data"
        )
    except Exception as e:
        logger.error(f"Error updating bug: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update bug"
        )


@router.patch("/bugs/{bug_id}/severity", response_model=BugResponse)
async def update_bug_severity(
    request: Request,
    bug_id: UUID,
    project_id: UUID,
    payload: BugSeverityUpdate,
    user: dict = Depends(get_current_user)
):
    """Update bug severity (all roles)"""
    try:
        ensure_project_role(
            supabase,
            project_id,
            user["user_id"],
            ["owner", "admin", "developer", "reporter"],
        )
        current_bug = bug.get_bug(supabase, bug_id, project_id)
        if not current_bug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bug not found"
            )

        updated = bug.update_bug(supabase, bug_id, BugUpdate(severity=payload.severity))
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bug not found"
            )

        if current_bug.get("severity") != payload.severity:
            log_bug_updated(
                bug_id,
                user["user_id"],
                {"severity": payload.severity},
                get_client_ip(request)
            )

        full_bug = bug.get_bug(supabase, bug_id, project_id)
        return BugResponse(**full_bug)
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error updating bug severity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data"
        )
    except Exception as e:
        logger.error(f"Error updating bug severity: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update bug severity"
        )

@router.delete("/bugs/{bug_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bug(
    bug_id: UUID,
    project_id: UUID,
    user: dict = Depends(get_current_user)
):
    """Delete a bug (admin only)"""
    try:
        ensure_project_role(
            supabase,
            project_id,
            user["user_id"],
            ["owner", "admin"],
        )
        bug_row = bug.get_bug(supabase, bug_id, project_id)
        if not bug_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bug not found"
            )
        bug.delete_bug(supabase, bug_id)
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
