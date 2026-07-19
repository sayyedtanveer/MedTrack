#!/usr/bin/env python3
"""
ADMIN PASSWORD RESET UTILITY
============================
Use this tool to reset user passwords when admins forget them.
Since passwords are hashed with bcrypt (one-way), they CANNOT be decrypted.
Instead, this tool generates a new temporary password and resets the user's account.

Usage:
    python admin_password_reset.py --email user@example.com --new-password "TempPass123!"
    python admin_password_reset.py --email user@example.com --generate-temp
"""

import asyncio
import sys
import argparse
import secrets
import string
from typing import Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.app.config import settings
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher


class AdminPasswordReset:
    """Handle admin password reset operations."""

    def __init__(self):
        self.hasher = BcryptPasswordHasher()
        self.engine = None
        self.async_session = None

    async def init_db(self):
        """Initialize database connection."""
        database_url = settings.async_database_url or settings.database_url
        self.engine = create_async_engine(
            database_url,
            echo=False,
            future=True,
        )
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def find_user_by_email(self, email: str) -> Optional[dict]:
        """Find a user by email."""
        async with self.async_session() as session:
            result = await session.execute(
                text("SELECT id, email FROM users WHERE email = :email"),
                {"email": email},
            )
            row = result.fetchone()
            if not row:
                return None
            return {"id": row[0], "email": row[1]}

    async def reset_password(self, email: str, new_password: str) -> bool:
        """Reset user password and return success status."""
        try:
            user = await self.find_user_by_email(email)
            if not user:
                print(f"❌ ERROR: User with email '{email}' not found")
                return False

            # Hash the new password
            hashed_password = self.hasher.hash(new_password)

            # Update in database directly
            async with self.async_session() as session:
                await session.execute(
                    text(
                        "UPDATE users SET hashed_password = :hashed_password, updated_at = NOW() WHERE email = :email"
                    ),
                    {"hashed_password": hashed_password, "email": email},
                )
                await session.commit()

            print(f"✅ SUCCESS: Password reset for {email}")
            print(f"   New Password: {new_password}")
            print(f"   Status: Active")
            return True

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            return False

    async def generate_temporary_password(self) -> str:
        """Generate a secure temporary password."""
        # Generate password with uppercase, lowercase, numbers, and special chars
        chars = string.ascii_letters + string.digits + "!@#$%"
        password = ''.join(secrets.choice(chars) for _ in range(16))
        return password

    async def reset_with_temp_password(self, email: str) -> Optional[str]:
        """Reset user password with a temporary one and return the temp password."""
        temp_password = await self.generate_temporary_password()
        success = await self.reset_password(email, temp_password)
        return temp_password if success else None

    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()


async def main():
    parser = argparse.ArgumentParser(
        description="Admin Password Reset Tool - Securely reset user passwords"
    )
    parser.add_argument(
        "--email", "-e",
        required=True,
        help="User email address"
    )
    parser.add_argument(
        "--new-password", "-p",
        help="New password (if not provided, will execute in test mode)"
    )
    parser.add_argument(
        "--generate-temp", "-g",
        action="store_true",
        help="Generate a temporary password instead of using --new-password"
    )

    args = parser.parse_args()

    reset_tool = AdminPasswordReset()
    await reset_tool.init_db()

    try:
        if args.generate_temp:
            print(f"\n🔄 Generating temporary password for {args.email}...")
            temp_password = await reset_tool.reset_with_temp_password(args.email)
            if temp_password:
                print(f"   📋 Temporary Password: {temp_password}")
                print(f"   ⚠️  Share this with the user securely")
                print(f"   ⚠️  User should change it on first login\n")
        elif args.new_password:
            print(f"\n🔄 Resetting password for {args.email}...")
            await reset_tool.reset_password(args.email, args.new_password)
            print()
        else:
            print("❌ ERROR: Provide either --new-password or --generate-temp")
            sys.exit(1)

    finally:
        await reset_tool.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  ADMIN PASSWORD RESET TOOL")
    print("="*60)
    print("\n⚠️  NOTE: Passwords are HASHED (one-way), not encrypted.")
    print("    This tool generates a NEW password - it cannot decrypt.\n")

    asyncio.run(main())
