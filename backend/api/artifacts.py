from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from uuid import UUID
from typing import Optional
from backend.dependencies import get_current_user, role_required, supabase
from backend.schemas.artifact import ArtifactCreate, ArtifactUpdate, ArtifactResponse
from backend.crud import artifact
from backend.utils.audit_log import log_artifact_created, log_artifact_updated, get_client_ip
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/artifacts", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    request: Request,
    artifact_data: ArtifactCreate,
    user: dict = Depends(role_required(["reporter", "developer", "admin"]))
):
    """Create a new artifact"""
    try:
        created = artifact.create_artifact(supabase, artifact_data, UUID(user["user_id"]))
        
        # Audit logging
        log_artifact_created(UUID(created["id"]), user["user_id"], get_client_ip(request))
        
        return ArtifactResponse(**created)
    except ValueError as e:
        logger.warning(f"Validation error creating artifact: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data"
        )
    except Exception as e:
        logger.error(f"Error creating artifact: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create artifact"
        )

@router.get("/artifacts", response_model=list[ArtifactResponse])
async def list_artifacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """List all artifacts"""
    try:
        artifacts = artifact.get_artifacts(supabase, skip, limit)
        return [ArtifactResponse(**a) for a in artifacts]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: UUID,
    user: dict = Depends(get_current_user)
):
    """Get a single artifact by ID"""
    try:
        artifact_data = artifact.get_artifact(supabase, artifact_id)
        if not artifact_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artifact not found"
            )
        return ArtifactResponse(**artifact_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.patch("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(
    artifact_id: UUID,
    artifact_data: ArtifactUpdate,
    user: dict = Depends(get_current_user)
):
    """Update an artifact (admin or creator only)"""
    try:
        # Check if artifact exists and get creator
        existing = artifact.get_artifact(supabase, artifact_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artifact not found"
            )
        
        # Check permissions: admin can update any, creator can update their own
        if user["role"] != "admin" and existing["created_by"] != user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this artifact"
            )
        
        updated = artifact.update_artifact(supabase, artifact_id, artifact_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artifact not found"
            )
        return ArtifactResponse(**updated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    artifact_id: UUID,
    user: dict = Depends(role_required(["admin"]))
):
    """Delete an artifact (admin only)"""
    try:
        artifact.delete_artifact(supabase, artifact_id)
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
