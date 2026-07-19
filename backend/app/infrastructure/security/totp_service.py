"""
TOTP Service for Two-Factor Authentication

Provides TOTP secret generation, QR code generation, verification,
and backup code management.
"""

import secrets
import string
from typing import List, Tuple
import io

import pyotp
import qrcode


class TOTPService:
    """
    Service for managing TOTP (Time-based One-Time Password) authentication.
    """

    @staticmethod
    def generate_secret() -> str:
        """
        Generate a random TOTP secret (base32 encoded).

        Returns:
            str: 32-character base32 encoded secret
        """
        return pyotp.random_base32()

    @staticmethod
    def generate_totp(secret: str) -> pyotp.TOTP:
        """
        Create a TOTP object from secret.

        Args:
            secret: Base32 encoded TOTP secret

        Returns:
            pyotp.TOTP: TOTP object for verification/generation
        """
        return pyotp.TOTP(secret)

    @staticmethod
    def verify_totp(secret: str, code: str, window: int = 1) -> bool:
        """
        Verify a TOTP code against the secret.

        Args:
            secret: Base32 encoded TOTP secret
            code: 6-digit code to verify
            window: Number of time windows to check (for clock skew)
                   window=1 checks current, previous, and next time window

        Returns:
            bool: True if code is valid, False otherwise
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)

    @staticmethod
    def get_totp_uri(secret: str, email: str, issuer_name: str = "MedTrack") -> str:
        """
        Generate provisioning URI for QR code.

        Args:
            secret: Base32 encoded TOTP secret
            email: User's email address (used as account identifier)
            issuer_name: Name of the service (shown in authenticator app)

        Returns:
            str: otpauth:// URI for QR code
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=email,
            issuer_name=issuer_name,
        )

    @staticmethod
    def generate_qr_code(uri: str) -> bytes:
        """
        Generate QR code image as PNG bytes.

        Args:
            uri: otpauth:// URI from get_totp_uri()

        Returns:
            bytes: PNG image data
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to PNG bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        return img_bytes.getvalue()

    @staticmethod
    def generate_backup_codes(count: int = 10, code_length: int = 8) -> List[str]:
        """
        Generate one-time backup codes for account recovery.

        Args:
            count: Number of backup codes to generate
            code_length: Length of each code

        Returns:
            List[str]: List of backup codes in format "XXXX-XXXX"
        """
        charset = string.ascii_uppercase + string.digits
        # Remove confusing characters: 0, O, 1, I, L
        charset = charset.replace("0", "").replace("O", "").replace("1", "").replace("I", "").replace("L", "")

        codes = []
        for _ in range(count):
            # Generate random code
            code = "".join(secrets.choice(charset) for _ in range(code_length))

            # Format as pairs: "XXXX-XXXX"
            formatted = "-".join([code[i : i + 4] for i in range(0, len(code), 4)])
            codes.append(formatted)

        return codes

    @staticmethod
    def format_backup_code(code: str) -> str:
        """
        Normalize backup code for comparison (remove dashes, uppercase).

        Args:
            code: Backup code with or without dashes

        Returns:
            str: Normalized code
        """
        return code.replace("-", "").replace(" ", "").upper()

    @staticmethod
    def verify_backup_code(provided_code: str, stored_codes: List[str]) -> Tuple[bool, List[str]]:
        """
        Verify a backup code and remove it from the list if valid.

        Args:
            provided_code: Backup code provided by user
            stored_codes: List of unused backup codes stored in DB

        Returns:
            Tuple[bool, List[str]]: (is_valid, remaining_codes)
        """
        normalized_provided = TOTPService.format_backup_code(provided_code)

        for i, stored_code in enumerate(stored_codes):
            normalized_stored = TOTPService.format_backup_code(stored_code)
            if normalized_provided == normalized_stored:
                # Found match - remove from list
                remaining = stored_codes[:i] + stored_codes[i + 1 :]
                return True, remaining

        # No match
        return False, stored_codes


# Convenience instance for injection
totp_service = TOTPService()
