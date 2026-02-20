# Security Implementation Guide

This document outlines the security measures implemented in the Bug Tracking System according to the Security & Data Protection Requirements (v1.1).

## Implemented Security Features

### 1. Input Validation & Data Sanitization

- **Pydantic Schemas**: All API endpoints use strict Pydantic models with field validators
- **Input Sanitization**: All text inputs are sanitized using `utils/security.py`:
  - HTML entity escaping to prevent XSS
  - Maximum length constraints
  - Enum value validation
  - URL/path sanitization
- **Validation Location**: Validation occurs in Pydantic models before any database interaction

### 2. SQL Injection Prevention

- **Supabase Client**: All database access uses Supabase's parameterized query builder
- **No Raw SQL**: No direct SQL string interpolation anywhere in the codebase
- **RLS Policies**: Row Level Security policies enforce data access at the database level

### 3. API Key & Secret Management

- **Environment Variables**: All secrets stored in `.env` files (not committed to git)
- **Frontend Safety**: Only public Supabase anon key exposed to frontend
- **Backend Secrets**: Service role key only accessible to backend
- **Error Handling**: Error messages never expose API keys or secrets

### 4. Secure API Design

- **Rate Limiting**: Implemented via `middleware/rate_limit.py`:
  - Auth endpoints: 5 requests/minute
  - Bug/Artifact endpoints: 20 requests/minute
  - Default: 30 requests/minute
- **Error Handling**: Generic error messages returned to clients; detailed errors logged server-side
- **CORS**: Restricted to configured origins only

### 5. Authentication & Authorization

- **JWT Validation**: All protected endpoints validate Supabase JWT tokens
- **Role-Based Access**: Server-side RBAC enforced via `role_required` dependency
- **No Frontend-Only Checks**: All authorization verified on backend

### 6. Audit Logging

- **Comprehensive Logging**: All critical actions logged via `utils/audit_log.py`:
  - Bug creation/updates/status changes
  - Artifact creation/updates
  - Authentication events
- **Log Format**: Includes user ID, timestamp, resource type, action, and IP address
- **Log File**: Audit logs written to `audit.log`

### 7. Cross-Site Protections

- **XSS Prevention**: All user input HTML-escaped before storage/display
- **CSRF Protection**: Stateless JWT-based authentication reduces CSRF risk
- **Content Security**: No raw HTML rendering of user input

### 8. Error Handling

- **Generic Messages**: Clients receive generic error messages
- **Internal Logging**: Detailed errors logged server-side only
- **Exception Handlers**: Global exception handlers prevent information leakage

## Security Testing

Run security tests with:
```bash
cd backend
pytest tests/test_security.py -v
```

Tests cover:
- SQL injection prevention
- XSS prevention
- Input validation
- Rate limiting
- Unauthorized access
- Role-based access control
- Error message sanitization

## Configuration

### Environment Variables

Required environment variables (never commit these):
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Service role key (backend only)
- `ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins
- `ENVIRONMENT`: Set to "production" to disable API docs

### Rate Limiting Configuration

Modify `middleware/rate_limit.py` to adjust rate limits:
```python
RATE_LIMITS = {
    "/api/auth": {"requests": 5, "window": 60},
    "/api/bugs": {"requests": 20, "window": 60},
    # ...
}
```

## Monitoring & Auditing

### Audit Logs

Audit logs are written to `backend/audit.log`. Monitor for:
- Failed authentication attempts
- Unusual access patterns
- Privilege escalation attempts
- Data modification events

### Log Rotation

In production, implement log rotation to prevent disk space issues:
```bash
# Example logrotate configuration
/var/log/bugtracker/audit.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
}
```

## Security Checklist

Before deploying to production:

- [ ] All environment variables set and secure
- [ ] CORS origins restricted to production domains
- [ ] API docs disabled in production (`ENVIRONMENT=production`)
- [ ] Rate limiting configured appropriately
- [ ] Audit logging enabled and monitored
- [ ] HTTPS enforced (via reverse proxy/load balancer)
- [ ] Dependencies updated to latest secure versions
- [ ] Security tests passing
- [ ] RLS policies verified in Supabase
- [ ] Error handling verified (no information leakage)

## Reporting Security Issues

If you discover a security vulnerability, please report it responsibly. Do not create public GitHub issues for security vulnerabilities.
