# Admin Password Management Guide

## ⚠️ IMPORTANT: Why Passwords Cannot Be Decrypted

Your MedTrack system uses **bcrypt with 12 rounds** — a one-way cryptographic hash. This means:

| Aspect | Details |
|--------|---------|
| **Storage Method** | Bcrypt Hashing (one-way) |
| **Can Be Decrypted?** | ❌ **NO** — by design |
| **Why?** | This is the CORRECT security practice |
| **What You Can Do** | ✅ Reset to a new password |
| **What You Cannot Do** | ❌ Retrieve original password |

---

## Method 1: CLI Tool (Command Line)

### Option A: Generate Temporary Password

```bash
cd c:\Users\sayye\source\repos\MedTrack\backend
python admin_password_reset.py --email admin@medtrack-demo.com --generate-temp
```

**Output:**
```
✅ SUCCESS: Password reset for admin@medtrack-demo.com
   New Password: Kx4!mP9vL2$nQ8wR
   Status: Active
```

### Option B: Set Custom Password

```bash
python admin_password_reset.py --email admin@medtrack-demo.com --new-password "MyNewPassword123!"
```

**For Windows PowerShell:**
```powershell
cd backend
.\.venv\Scripts\python.exe admin_password_reset.py --email admin@medtrack-demo.com --generate-temp
```

---

## Method 2: API Endpoint (Recommended for Admin Panel)

### First, Register the Router in main.py

1. Open `backend/app/main.py`
2. Add these lines where you register other routers:

```python
from backend.app.interfaces.http.routes.admin_password_reset_router import router as admin_reset_router

# Add this in your app setup:
app.include_router(admin_reset_router, prefix="/api/v1/admin", tags=["admin"])
```

### API Endpoint: Reset Password with Temporary Password

**Endpoint:** `POST /api/v1/admin/password/reset`

**Authentication:** Requires admin JWT token

**Request:**
```json
{
  "email": "user@example.com",
  "generate_temp": true
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Password successfully reset for user@example.com",
  "temporary_password": "Kx4!mP9vL2$nQ8wR",
  "email": "user@example.com"
}
```

---

## Method 3: Frontend Admin Panel (Coming Soon)

You can add this to your admin dashboard. Create a form with:

1. **User Email Input** - which user to reset
2. **Generate Temp Password** - auto-generates secure password
3. **Or Set Custom Password** - admin enters custom password
4. **Reset Button** - calls the API endpoint

### Example Frontend Component

```tsx
// You can add this to your admin panel
const [resetEmail, setResetEmail] = useState("");
const [tempPassword, setTempPassword] = useState("");

const handleReset = async () => {
  const response = await fetch("/api/v1/admin/password/reset", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${adminToken}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      email: resetEmail,
      generate_temp: true
    })
  });

  const data = await response.json();
  if (data.success) {
    setTempPassword(data.temporary_password);
    alert(`Reset successful! Temp password: ${data.temporary_password}`);
  }
};
```

---

## Security Best Practices

### ✅ DO:

- ✅ Generate secure temporary passwords (16 characters minimum)
- ✅ Share temporary passwords through secure channels (SMS, email)
- ✅ Force users to change password on first login after reset
- ✅ Log all password resets with admin username and timestamp
- ✅ Use the API endpoint for admin panel (REST API is more secure than CLI)
- ✅ Restrict password reset endpoint to admin users only
- ✅ Use HTTPS in production (not HTTP)

### ❌ DON'T:

- ❌ Try to decrypt passwords (technically impossible with bcrypt)
- ❌ Store temporary passwords in plaintext
- ❌ Allow users to set weak passwords
- ❌ Share passwords via unencrypted email
- ❌ Expose password reset endpoint to non-admins
- ❌ Log passwords anywhere (not even hashed ones)

---

## Troubleshooting

### Problem: "User with email 'X' not found"
**Solution:** Verify the email address is correct (case-sensitive)

### Problem: "UnicodeEncodeError" in PowerShell
**Solution:** Use Python's `-c` flag properly:
```powershell
python.exe admin_password_reset.py -e admin@test.com -g
```

### Problem: Database Connection Error
**Solution:** Make sure:
1. PostgreSQL is running
2. `.env` file has correct `DATABASE_URL`
3. Venv is activated: `.\.venv\Scripts\Activate.ps1`

---

## Password Reset Workflow Example

```
SCENARIO: Admin forgets password

1. Admin (or another admin) runs:
   python admin_password_reset.py -e admin@medtrack-demo.com -g

2. Temporary password is displayed:
   Kx4!mP9vL2$nQ8wR

3. Original admin logs in with:
   Email: admin@medtrack-demo.com
   Password: Kx4!mP9vL2$nQ8wR

4. System prompts to change password on login

5. Admin sets their own permanent password
```

---

## Files Created

1. **`backend/admin_password_reset.py`** - CLI tool for password reset
2. **`backend/app/interfaces/http/routes/admin_password_reset_router.py`** - API endpoints
3. **`ADMIN_PASSWORD_MANAGEMENT.md`** - This guide

---

## Next Steps

1. ✅ If you forgot password now: Use the CLI tool above
2. ⏳ Integrate API endpoint into admin panel (optional but recommended)
3. ⏳ Add "Force Password Change on Next Login" feature (enhanced security)
4. ⏳ Add password reset audit logging

---

## Questions?

- **Why bcrypt?** Industry standard, slow hashing by design prevents brute-force attacks
- **Can I switch to encryption?** Not recommended - bcrypt is more secure for passwords
- **What about 2FA?** Check `backend/app/infrastructure/security/totp_service.py`
