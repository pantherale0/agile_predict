# OAuth2 / OIDC Authentication Setup

This guide explains how to configure external OAuth2/OIDC authentication with your FastAPI application using providers like Authentik, Azure Entra, or Google SSO.

## Overview

The application now uses external OIDC providers for Single Sign-On (SSO) to protect admin endpoints:
- **Public endpoints**: `/api/prices/*` and `/api/forecasts/*` - No authentication required
- **Protected endpoints**: `/api/tasks/*` and `/scheduler-status` - Requires OAuth2 authentication
- **Admin-only endpoints**: Job trigger actions - Require admin group membership

## Configuration

### 1. Environment Variables

Update `backend_fastapi/.env` with your OIDC provider details:

```env
# OAuth2 / OIDC Configuration
OAUTH2_ENABLED=true
OAUTH2_PROVIDER=authentik  # or 'azure', 'google', etc.
OAUTH2_CLIENT_ID=your-client-id-here
OAUTH2_CLIENT_SECRET=your-client-secret-here
OAUTH2_DISCOVERY_URL=https://authentik.example.com/application/o/
OAUTH2_REDIRECT_URI=http://localhost:8000/api/auth/callback
OAUTH2_ADMIN_GROUP=admin

# JWT Configuration
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Provider-Specific Setup

### Authentik

1. **Create OAuth2/OpenID Application in Authentik**:
   - Navigate to Applications → Applications
   - Create new application
   - Set authorization flow to "Authorization Code"
   - Set redirect URIs: `http://localhost:8000/api/auth/callback`

2. **Configure credentials**:
   ```env
   OAUTH2_PROVIDER=authentik
   OAUTH2_CLIENT_ID=<from Authentik app>
   OAUTH2_CLIENT_SECRET=<from Authentik app>
   OAUTH2_DISCOVERY_URL=https://your-authentik-domain/application/o/
   OAUTH2_ADMIN_GROUP=admin-group  # Must match your Authentik group name
   ```

3. **Add groups to Authentik**:
   - Create a group named "admin" (or your preferred name)
   - Add users to this group for admin access

### Azure Entra ID (formerly Azure AD)

1. **Register Application**:
   - Go to Azure AD → App registrations
   - Create new registration
   - Add Redirect URI: `http://localhost:8000/api/auth/callback`

2. **Configure credentials**:
   ```env
   OAUTH2_PROVIDER=azure
   OAUTH2_CLIENT_ID=<Application ID>
   OAUTH2_CLIENT_SECRET=<Client secret value>
   OAUTH2_DISCOVERY_URL=https://login.microsoftonline.com/<tenant-id>/v2.0/
   OAUTH2_ADMIN_GROUP=<group-object-id>  # Use group object ID for admin group
   ```

3. **API Permissions**:
   - Add permissions: `openid`, `profile`, `email`, `User.Read`
   - For group membership: Add `Directory.Read.All` (Application)

### Google OAuth2

1. **Create OAuth2 Credentials**:
   - Go to Google Cloud Console → APIs & Services → Credentials
   - Create OAuth 2.0 Client ID (Web application)
   - Add Authorized redirect URIs: `http://localhost:8000/api/auth/callback`

2. **Configure credentials**:
   ```env
   OAUTH2_PROVIDER=google
   OAUTH2_CLIENT_ID=<client-id>.apps.googleusercontent.com
   OAUTH2_CLIENT_SECRET=<client-secret>
   OAUTH2_DISCOVERY_URL=https://accounts.google.com
   OAUTH2_ADMIN_GROUP=admin  # Not applicable for Google; manage admin users differently
   ```

## API Usage

### Login Flow

1. **Initiate Login**:
   ```bash
   GET /api/auth/login
   ```
   Redirects to your OIDC provider's login page

2. **Callback Handling**:
   Provider redirects back to `/api/auth/callback` with authorization code
   Application exchanges code for access token
   Token is stored in browser localStorage

### Using Protected Endpoints

Include the access token in API requests:

```bash
curl -H "Authorization: Bearer <access_token>" \
     http://localhost:8000/api/tasks/scheduler/status
```

### Token-Based Requests

```javascript
// Frontend example
const token = localStorage.getItem('access_token');
const response = await fetch('/api/tasks/scheduler/status', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

## Endpoint Protection

### Public Endpoints (No Authentication)
- `GET /health` - Health check
- `GET /api/prices/*` - Price history
- `GET /api/forecasts/*` - Forecast data

### Protected Endpoints (Requires OAuth2 Token)
- `GET /scheduler-status` - Scheduler status page
- `GET /api/tasks/scheduler/status` - Scheduler status JSON
- `GET /api/tasks/jobs` - List all jobs
- `GET /api/tasks/jobs/{job_id}/details` - Job details
- `GET /api/tasks/status/summary` - Job execution summary

### Admin-Only Endpoints (Requires Admin Group)
- `POST /api/tasks/jobs/{job_id}/trigger` - Trigger a job
- Job trigger actions on `/scheduler-status` page

## Token Claims

The system extracts the following from OIDC tokens:

- `preferred_username` or `email` - User identifier
- `email` - User email address
- `groups` - User group memberships (array)

Admin access is determined by group membership matching `OAUTH2_ADMIN_GROUP`.

## Development Testing

For local development without a real OIDC provider:

1. Set `OAUTH2_ENABLED=false` in `.env`
2. Use simple token-based auth for testing
3. Consider using Authentik in Docker for local testing

## Production Deployment

1. **Use HTTPS only**:
   - Update `OAUTH2_REDIRECT_URI` to use `https://`
   - Ensure all OIDC endpoints use HTTPS

2. **Secure secrets**:
   - Store `SECRET_KEY` and `OAUTH2_CLIENT_SECRET` in secure vault
   - Rotate secrets regularly
   - Never commit secrets to version control

3. **Token expiration**:
   - Set appropriate `ACCESS_TOKEN_EXPIRE_MINUTES`
   - Implement token refresh mechanism if needed

4. **CORS configuration**:
   - Update `CORS_ORIGINS` to match your frontend domain
   - Restrict origins in production

## Troubleshooting

### "Could not validate credentials"
- Check token signature validation
- Verify OAUTH2_DISCOVERY_URL is correct
- Ensure JWKS endpoint is accessible

### "OAUTH2 is not configured"
- Verify `OAUTH2_ENABLED=true` in .env
- Check `OAUTH2_DISCOVERY_URL` is set and valid

### Group membership not recognized
- Verify `OAUTH2_ADMIN_GROUP` matches provider group name
- Check token includes groups claim
- Confirm user is member of group in provider

### Token expires too quickly
- Increase `ACCESS_TOKEN_EXPIRE_MINUTES`
- Implement refresh token flow if needed

## Next Steps

1. Configure your OIDC provider
2. Set environment variables
3. Test login flow: `GET /api/auth/login`
4. Test protected endpoints with token
5. Verify group-based admin access works
