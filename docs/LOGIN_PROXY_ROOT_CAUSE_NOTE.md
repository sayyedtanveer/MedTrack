# Login UI 500 Root Cause Note

Date: 2026-07-05

## Issue
The frontend login page was failing with a 500 error even though the backend login endpoint worked directly.

## Root cause
The Vite frontend dev proxy was targeting the wrong backend port for API requests. The login request from the UI was reaching the frontend dev server, but the proxy was not forwarding it correctly to the backend, so the browser saw a 500 response.

## What was verified
- Direct backend login endpoint worked:
  - POST /api/v1/auth/login returned a JWT successfully
  - GET /api/v1/auth/me returned 200 with the authenticated user profile
- The UI login flow then completed successfully after the proxy target was corrected.

## Fix applied
- Updated the Vite dev proxy target to the actual backend endpoint:
  - http://127.0.0.1:8001
- Restarted the frontend dev server so the new proxy configuration was active.

## Files involved
- frontend/vite.config.js
- frontend/vite.config.ts

## Prevention
If the backend port changes again, verify both:
1. The backend is running on the expected port
2. The frontend Vite proxy target matches that port

## How to know the backend port changed
Use one or more of these checks:
- Run the backend and confirm the startup log shows the port, for example: `Uvicorn running on http://0.0.0.0:8001`
- Check which port the backend is listening on with:
  - `Get-NetTCPConnection -LocalPort 8000,8001,8002 -State Listen`
- Verify the frontend proxy setting in [frontend/.env](frontend/.env):
  - `VITE_API_TARGET=http://127.0.0.1:<port>`
- Test the API directly from the browser/dev terminal:
  - `curl http://localhost:<port>/api/v1/auth/me`

## What to do when the port changes
1. Update `VITE_API_TARGET` in [frontend/.env](frontend/.env) to the new backend URL.
2. Restart the frontend dev server.
3. Re-test login from the UI.
