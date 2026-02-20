from supabase import Client
from uuid import UUID
from typing import Optional, List
from datetime import datetime, date
from backend.schemas.bug import BugCreate, BugUpdate

def create_bug(db: Client, bug_data: BugCreate, reporter_id: UUID):
    """Create a new bug and its artifact relationships"""
    # Create bug
    bug_result = db.table("bugs").insert({
        "title": bug_data.title,
        "description": bug_data.description,
        "bug_type": bug_data.bug_type,
        "status": bug_data.status or "open",
        "reporter_id": str(reporter_id),
        "assigned_to": str(bug_data.assigned_to) if bug_data.assigned_to else None
    }).execute()
    
    if not bug_result.data:
        raise Exception("Failed to create bug")
    
    bug = bug_result.data[0]
    bug_id = bug["id"]
    
    # Create artifact relationships
    if bug_data.artifact_ids:
        artifact_relations = [
            {"bug_id": bug_id, "artifact_id": str(artifact_id)}
            for artifact_id in bug_data.artifact_ids
        ]
        db.table("bug_artifacts").insert(artifact_relations).execute()
    
    return bug

def get_bug(db: Client, bug_id: UUID):
    """Get a single bug with associated artifacts"""
    bug_result = db.table("bugs").select("*").eq("id", str(bug_id)).single().execute()
    
    if not bug_result.data:
        return None
    
    bug = bug_result.data
    
    # Get associated artifacts
    artifacts_result = db.table("bug_artifacts").select("artifact_id, artifacts(*)").eq("bug_id", str(bug_id)).execute()
    bug["artifacts"] = [item["artifacts"] for item in artifacts_result.data if item.get("artifacts")]
    
    return bug

def get_bugs(
    db: Client,
    skip: int = 0,
    limit: int = 100,
    status: Optional[List[str]] = None,
    bug_type: Optional[List[str]] = None,
    reporter_id: Optional[UUID] = None,
    assigned_to: Optional[UUID] = None,
    artifact_type: Optional[List[str]] = None,
    found_at_from: Optional[datetime] = None,
    found_at_to: Optional[datetime] = None
):
    """Get bugs with filtering"""
    query = db.table("bugs").select("*")
    
    if status:
        query = query.in_("status", status)
    if bug_type:
        query = query.in_("bug_type", bug_type)
    if reporter_id:
        query = query.eq("reporter_id", str(reporter_id))
    if assigned_to:
        query = query.eq("assigned_to", str(assigned_to))
    if found_at_from:
        query = query.gte("found_at", found_at_from.isoformat())
    if found_at_to:
        query = query.lte("found_at", found_at_to.isoformat())
    
    # Handle artifact_type filtering (requires join)
    if artifact_type:
        # Get bug IDs that have artifacts of the specified types
        artifacts_result = db.table("artifacts").select("id").in_("type", artifact_type).execute()
        artifact_ids = [a["id"] for a in artifacts_result.data]
        
        if artifact_ids:
            bug_artifacts_result = db.table("bug_artifacts").select("bug_id").in_("artifact_id", artifact_ids).execute()
            bug_ids = list(set([ba["bug_id"] for ba in bug_artifacts_result.data]))
            if bug_ids:
                query = query.in_("id", bug_ids)
            else:
                # No bugs match, return empty
                return []
        else:
            return []
    
    result = query.order("created_at", desc=True).range(skip, skip + limit - 1).execute()
    return result.data

def update_bug(db: Client, bug_id: UUID, bug_data: BugUpdate):
    """Update a bug and handle fixed_at based on status"""
    update_data = {}
    
    if bug_data.title is not None:
        update_data["title"] = bug_data.title
    if bug_data.description is not None:
        update_data["description"] = bug_data.description
    if bug_data.bug_type is not None:
        update_data["bug_type"] = bug_data.bug_type
    if bug_data.assigned_to is not None:
        update_data["assigned_to"] = str(bug_data.assigned_to) if bug_data.assigned_to else None
    
    # Handle status change and fixed_at
    if bug_data.status is not None:
        update_data["status"] = bug_data.status
        
        # Get current bug to check previous status
        current_bug = db.table("bugs").select("status").eq("id", str(bug_id)).single().execute()
        previous_status = current_bug.data.get("status") if current_bug.data else None
        
        if bug_data.status == "fixed" and previous_status != "fixed":
            update_data["fixed_at"] = datetime.utcnow().isoformat()
        elif bug_data.status != "fixed" and previous_status == "fixed":
            update_data["fixed_at"] = None
    
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    result = db.table("bugs").update(update_data).eq("id", str(bug_id)).execute()
    
    if not result.data:
        return None
    
    # Update artifact relationships if provided
    if bug_data.artifact_ids is not None:
        # Delete existing relationships
        db.table("bug_artifacts").delete().eq("bug_id", str(bug_id)).execute()
        
        # Create new relationships
        if bug_data.artifact_ids:
            artifact_relations = [
                {"bug_id": str(bug_id), "artifact_id": str(artifact_id)}
                for artifact_id in bug_data.artifact_ids
            ]
            db.table("bug_artifacts").insert(artifact_relations).execute()
    
    return result.data[0]

def delete_bug(db: Client, bug_id: UUID):
    """Delete a bug and its relationships"""
    # Delete relationships first
    db.table("bug_artifacts").delete().eq("bug_id", str(bug_id)).execute()
    
    # Delete bug
    result = db.table("bugs").delete().eq("id", str(bug_id)).execute()
    return result.data
