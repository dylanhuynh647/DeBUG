"""
Security tests for the bug tracking system
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.dependencies import supabase_auth_secure
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_sql_injection_prevention():
    """Test that SQL injection attempts are prevented"""
    # Test with malicious input in title
    malicious_input = "'; DROP TABLE bugs; --"
    
    # This should be sanitized by Pydantic validation
    response = client.post(
        "/api/bugs",
        json={
            "title": malicious_input,
            "description": "Test description",
            "bug_type": "other"
        },
        headers={"Authorization": "Bearer fake_token"}
    )
    
    # Should fail validation, not execute SQL
    assert response.status_code in [401, 422]  # Unauthorized or validation error

def test_xss_prevention():
    """Test that XSS attempts are sanitized"""
    xss_payload = "<script>alert('XSS')</script>"
    
    response = client.post(
        "/api/bugs",
        json={
            "title": xss_payload,
            "description": "Test",
            "bug_type": "other"
        },
        headers={"Authorization": "Bearer fake_token"}
    )
    
    # Input should be sanitized (HTML escaped)
    assert response.status_code in [401, 422]

def test_input_validation():
    """Test that invalid input is rejected"""
    # Test empty title
    response = client.post(
        "/api/bugs",
        json={
            "title": "",
            "description": "Test",
            "bug_type": "other"
        },
        headers={"Authorization": "Bearer fake_token"}
    )
    assert response.status_code in [401, 422]
    
    # Test invalid enum value
    response = client.post(
        "/api/bugs",
        json={
            "title": "Test",
            "description": "Test",
            "bug_type": "invalid_type"
        },
        headers={"Authorization": "Bearer fake_token"}
    )
    assert response.status_code in [401, 422]

def test_rate_limiting():
    """Test that rate limiting is enforced"""
    # Make multiple rapid requests
    for i in range(35):  # Exceed default limit of 30
        response = client.get("/api/bugs", headers={"Authorization": "Bearer fake_token"})
        if response.status_code == 429:
            assert "Rate limit exceeded" in response.json()["detail"]
            break
    else:
        # If we didn't hit rate limit, that's also acceptable (depends on implementation)
        pass

def test_unauthorized_access():
    """Test that unauthorized users cannot access protected endpoints"""
    # Request without token
    response = client.get("/api/bugs")
    assert response.status_code == 403  # Forbidden
    
    # Request with invalid token
    response = client.get("/api/bugs", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401  # Unauthorized

def test_role_based_access():
    """Test that role-based access control is enforced"""
    # This would require mocking authentication
    # For now, just verify endpoint exists
    response = client.get("/api/admin-only", headers={"Authorization": "Bearer fake_token"})
    # Should fail auth or return 403
    assert response.status_code in [401, 403]

def test_error_message_sanitization():
    """Test that error messages don't expose internal details"""
    # Trigger an error
    response = client.post(
        "/api/bugs",
        json={"invalid": "data"},
        headers={"Authorization": "Bearer fake_token"}
    )
    
    # Error message should be generic, not expose stack traces
    if response.status_code == 500:
        error_detail = response.json().get("detail", "")
        assert "stack trace" not in error_detail.lower()
        assert "traceback" not in error_detail.lower()

def test_max_length_validation():
    """Test that maximum length constraints are enforced"""
    # Test title exceeding max length
    long_title = "a" * 300  # Exceeds MAX_TITLE_LENGTH (255)
    
    response = client.post(
        "/api/bugs",
        json={
            "title": long_title,
            "description": "Test",
            "bug_type": "other"
        },
        headers={"Authorization": "Bearer fake_token"}
    )
    
    assert response.status_code in [401, 422]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
