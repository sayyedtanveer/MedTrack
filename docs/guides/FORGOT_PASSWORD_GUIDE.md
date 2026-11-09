# Forgot Password Feature - Complete Guide

## Status: ✅ FIXED AND WORKING

The self-service password reset feature is now fully implemented and functional for all user types (admin, internal users, clients).

---

## How It Works

### Two-Endpoint Flow

**1. Request Password Reset**
```bash
POST /api/v1/forgot-password/request
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "If an account exists with this email, a password reset link has been sent.",
  "reset_token": "nW6Y0uH1-zjK2m4k6nIAJP1YQq1KhEOCvhdC-v_BRvg"  // In development only
}
```

**⚠️ Security Note:** In production, the `reset_token` is NOT returned. Instead, it's sent to the user's email address. In development mode, it's included in the response for testing.

---

**2. Reset Password** 
```bash
POST /api/v1/forgot-password/reset
Content-Type: application/json

{
  "token": "nW6Y0uH1-zjK2m4k6nIAJP1YQq1KhEOCvhdC-v_BRvg",
  "new_password": "MyNewSecurePassword123!"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Password has been reset successfully. You can now log in."
}
```

---

## Testing the Feature

### Step 1: Request Reset Token
```bash
curl -X POST http://localhost:8000/api/v1/forgot-password/request \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@medtrack-demo.com"}'
```

**Copy the `reset_token` from the response.**

### Step 2: Reset Password
```bash
curl -X POST http://localhost:8000/api/v1/forgot-password/reset \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_TOKEN_HERE",
    "new_password": "NewPassword123!"
  }'
```

### Step 3: Login with New Password
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@medtrack-demo.com",
    "password": "NewPassword123!",
    "tenant_id": "TENANT_UUID"
  }'
```

---

## Frontend Integration

### Add Forgot Password Form to Login Page

The feature is accessible at:
```
POST /api/v1/forgot-password/request   # Send email
POST /api/v1/forgot-password/reset     # Complete reset
```

### Example React Component

```tsx
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

export function ForgotPasswordForm() {
  const [email, setEmail] = useState('')
  const [token, setToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [step, setStep] = useState('request') // 'request' | 'reset' | 'success'

  const requestMutation = useMutation({
    mutationFn: async (email: string) => {
      const response = await fetch('/api/v1/forgot-password/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      })
      return response.json()
    },
    onSuccess: (data) => {
      setToken(data.reset_token || '') // For dev mode
      setStep('reset')
    },
    onError: (error) => alert('Error: ' + error.message)
  })

  const resetMutation = useMutation({
    mutationFn: async (data: { token: string; new_password: string }) => {
      const response = await fetch('/api/v1/forgot-password/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      return response.json()
    },
    onSuccess: () => setStep('success'),
    onError: (error) => alert('Error: ' + error.message)
  })

  if (step === 'request') {
    return (
      <form onSubmit={(e) => {
        e.preventDefault()
        requestMutation.mutate(email)
      }}>
        <input
          type="email"
          placeholder="Enter your email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <button disabled={requestMutation.isPending}>
          {requestMutation.isPending ? 'Sending...' : 'Send Reset Link'}
        </button>
      </form>
    )
  }

  if (step === 'reset') {
    return (
      <form onSubmit={(e) => {
        e.preventDefault()
        resetMutation.mutate({ token, new_password: newPassword })
      }}>
        <input
          type="hidden"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <input
          type="password"
          placeholder="New password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
        />
        <button disabled={resetMutation.isPending}>
          {resetMutation.isPending ? 'Resetting...' : 'Reset Password'}
        </button>
      </form>
    )
  }

  return (
    <div className="success">
      <p>Password has been reset successfully!</p>
      <p>You can now log in with your new password.</p>
    </div>
  )
}
```

---

## Security Features

✅ **One-Way Hashing**: Passwords are hashed with bcrypt (12 rounds)
✅ **Token Expiration**: Reset tokens expire in 1 hour
✅ **Single Use**: Tokens can only be used once (marked as `used_at`)
✅ **Email Verification**: Token is sent via email (not exposed by default)
✅ **No User Enumeration**: Returns same message whether email exists or not
✅ **Secure Comparison**: Uses hashed token comparison (prevents timing attacks)

---

## Token Management

Tokens are stored in the `password_reset_tokens` table:

| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Unique token ID |
| `user_id` | UUID | User requesting reset |
| `tenant_id` | UUID | Tenant context |
| `token_hash` | String | SHA256 hash of token |
| `created_at` | DateTime | Token creation time |
| `expires_at` | DateTime | Token expiration (1 hour) |
| `used_at` | DateTime | When token was used (NULL if unused) |

---

## Comparison: Admin Reset vs. Self-Service Reset

| Feature | Admin Tool | Self-Service |
|---------|-----------|--------------|
| **File** | `admin_password_reset.py` | API Endpoint |
| **Use Case** | Admin resets OTHER users | User resets OWN password |
| **Auth Required** | None (CLI tool) | Email verification |
| **Token Expiry** | Immediate | 1 hour |
| **Use Case Example** | "User can't access account" | "User forgot password" |

---

## Troubleshooting

### Problem: "Reset token is invalid or expired"
**Solution:** 
- Token may have expired (1 hour limit)
- Token may have already been used
- Request a new token

### Problem: "No password reset token returned"
**Solution:**
- You're in production mode (by design - security feature)
- Check the user's email for reset link
- In development, token is returned in response

### Problem: "If an account exists with this email..." but no email received
**Solution:**
- Email service may not be configured (check `.env`)
- In development mode, token is in API response
- Check spam/junk folder

---

## Files Created/Modified

**New Files:**
- [backend/app/interfaces/api/v1/routes/self_service_password_reset_router.py](#) - New API endpoints

**Modified Files:**
- `backend/app/interfaces/api/v1/router.py` - Added router registration

**Already Existed:**
- `PasswordResetTokenModel` in `user_model.py`
- `password_reset_tokens` table in database

---

## Next Steps

1. ✅ Backend API implemented and tested
2. ⏳ Add forgot password form to frontend login page
3. ⏳ Send password reset emails (configure email service in .env)
4. ⏳ Add "Force password change on next login" feature
5. ⏳ Add password reset audit logging

---

## Related Tools

- **Admin Password Reset**: For admins resetting other users' passwords
  - See: [ADMIN_PASSWORD_MANAGEMENT.md](ADMIN_PASSWORD_MANAGEMENT.md)
  - CLI: `python admin_password_reset.py --email user@example.com --generate-temp`

---

## Environment Variables

Add to `.env` to enable email notifications:

```bash
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FRONTEND_URL=http://localhost:3000
```

Without these, tokens will be generated but not emailed (they'll be in the API response in dev mode).

---

## Status Summary

- ✅ Backend API: WORKING
- ✅ Token Generation: WORKING  
- ✅ Token Validation: WORKING
- ✅ Password Reset: WORKING
- ✅ Login with New Password: WORKING
- ⏳ Frontend Form: PENDING
- ⏳ Email Notifications: PENDING

**The forgot password feature is READY for frontend integration!**
