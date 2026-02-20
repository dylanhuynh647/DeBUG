"""
Audit logging system for security and compliance
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

# Configure audit logger
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Create file handler for audit logs
audit_handler = logging.FileHandler("audit.log")
audit_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
audit_handler.setFormatter(formatter)
audit_logger.addHandler(audit_handler)

def log_audit_event(
    event_type: str,
    user_id: Optional[str],
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    action: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
):
    """
    Log an audit event
    
    Args:
        event_type: Type of event (e.g., 'bug_created', 'bug_updated', 'auth_failed')
        user_id: ID of the user performing the action
        resource_type: Type of resource (e.g., 'bug', 'artifact')
        resource_id: ID of the resource
        action: Action performed (e.g., 'create', 'update', 'delete')
        details: Additional details as dictionary
        ip_address: IP address of the client
    """
    log_data = {
        "event_type": event_type,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat(),
        "resource_type": resource_type,
        "resource_id": resource_id,
        "action": action,
        "ip_address": ip_address,
    }
    
    if details:
        log_data["details"] = details
    
    # Format as JSON-like string for logging
    log_message = f"Event: {event_type} | User: {user_id} | Resource: {resource_type}/{resource_id} | Action: {action}"
    if details:
        log_message += f" | Details: {details}"
    if ip_address:
        log_message += f" | IP: {ip_address}"
    
    audit_logger.info(log_message)

def log_bug_created(bug_id: UUID, user_id: str, ip_address: Optional[str] = None):
    """Log bug creation"""
    log_audit_event(
        event_type="bug_created",
        user_id=user_id,
        resource_type="bug",
        resource_id=str(bug_id),
        action="create",
        ip_address=ip_address
    )

def log_bug_updated(bug_id: UUID, user_id: str, changes: Dict[str, Any], ip_address: Optional[str] = None):
    """Log bug update"""
    log_audit_event(
        event_type="bug_updated",
        user_id=user_id,
        resource_type="bug",
        resource_id=str(bug_id),
        action="update",
        details={"changes": changes},
        ip_address=ip_address
    )

def log_bug_status_changed(bug_id: UUID, user_id: str, old_status: str, new_status: str, ip_address: Optional[str] = None):
    """Log bug status change"""
    log_audit_event(
        event_type="bug_status_changed",
        user_id=user_id,
        resource_type="bug",
        resource_id=str(bug_id),
        action="status_change",
        details={"old_status": old_status, "new_status": new_status},
        ip_address=ip_address
    )

def log_bug_fixed(bug_id: UUID, user_id: str, ip_address: Optional[str] = None):
    """Log bug fix"""
    log_audit_event(
        event_type="bug_fixed",
        user_id=user_id,
        resource_type="bug",
        resource_id=str(bug_id),
        action="fix",
        ip_address=ip_address
    )

def log_artifact_created(artifact_id: UUID, user_id: str, ip_address: Optional[str] = None):
    """Log artifact creation"""
    log_audit_event(
        event_type="artifact_created",
        user_id=user_id,
        resource_type="artifact",
        resource_id=str(artifact_id),
        action="create",
        ip_address=ip_address
    )

def log_artifact_updated(artifact_id: UUID, user_id: str, changes: Dict[str, Any], ip_address: Optional[str] = None):
    """Log artifact update"""
    log_audit_event(
        event_type="artifact_updated",
        user_id=user_id,
        resource_type="artifact",
        resource_id=str(artifact_id),
        action="update",
        details={"changes": changes},
        ip_address=ip_address
    )

def log_auth_failed(email: Optional[str], reason: str, ip_address: Optional[str] = None):
    """Log failed authentication attempt"""
    log_audit_event(
        event_type="auth_failed",
        user_id=None,
        action="auth_failed",
        details={"email": email, "reason": reason},
        ip_address=ip_address
    )

def log_auth_success(user_id: str, ip_address: Optional[str] = None):
    """Log successful authentication"""
    log_audit_event(
        event_type="auth_success",
        user_id=user_id,
        action="auth_success",
        ip_address=ip_address
    )

def get_client_ip(request) -> Optional[str]:
    """Extract client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if hasattr(request, "client") and request.client:
        return request.client.host
    return None
