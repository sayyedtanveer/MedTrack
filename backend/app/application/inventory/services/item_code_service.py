from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.item_code_sequence_model import ItemCodeSequenceModel
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.infrastructure.persistence.models.material_category_model import MaterialCategoryModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.sales_models import ClientModel
from backend.app.infrastructure.persistence.models.number_series_models import (
    NumberSeriesConfigModel,
    NumberSeriesPrefixModel,
    NumberSeriesSequenceModel,
)
# Ensure TenantModel is registered in SQLAlchemy's mapper so that the FK on
# number_series_config.tenant_id → tenants.id can be resolved at flush time.
# Without this import the mapper raises NoReferencedTableError when ItemCodeService
# is used outside the full DI container.
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel as _TenantModel  # noqa: F401
from backend.app.application.inventory.services.number_series_audit_service import (
    NumberSeriesAuditService,
)

logger = logging.getLogger(__name__)

ITEM_TYPE_PREFIX = {
    "raw": "RM",
    "RAW": "RM",
    "rm": "RM",
    "finished": "FG",
    "finished_good": "FG",
    "FG": "FG",
    "semi_finished": "SF",
    "semi-finished": "SF",
    "SF": "SF",
}

# Default prefix mappings seeded on first access for the "material" entity type
DEFAULT_MATERIAL_PREFIXES: dict[str, str] = {
    "raw": "RM",
    "finished": "FG",
    "semi_finished": "SF",
    "consumable": "CON",
    "packaging": "PKG",
    "spare": "SPR",
}

# Default configs seeded on first access per tenant
DEFAULT_ENTITY_CONFIGS: dict[str, dict] = {
    "material": {"auto_generate": True, "prefix": "", "include_abbreviation": True, "manual_override": "never"},
    "purchase_order": {"auto_generate": True, "prefix": "PO", "include_abbreviation": False, "manual_override": "never"},
    "sales_order": {"auto_generate": True, "prefix": "SO", "include_abbreviation": False, "manual_override": "never"},
    "invoice": {"auto_generate": True, "prefix": "INV", "include_abbreviation": False, "manual_override": "never"},
    "grn": {"auto_generate": True, "prefix": "GRN", "include_abbreviation": False, "manual_override": "never"},
    "work_order": {"auto_generate": True, "prefix": "WO", "include_abbreviation": False, "manual_override": "never"},
    "batch": {"auto_generate": True, "prefix": "BAT", "include_abbreviation": False, "manual_override": "never"},
    "customer": {"auto_generate": True, "prefix": "CUST", "include_abbreviation": False, "manual_override": "admin_only"},
    "supplier": {"auto_generate": True, "prefix": "SUP", "include_abbreviation": False, "manual_override": "admin_only"},
}

MAX_GENERATION_ATTEMPTS = 100

# Regex for valid manual code format: alphanumeric, hyphens, and underscores only
MANUAL_CODE_PATTERN = re.compile(r'^[A-Za-z0-9\-_]+$')
MANUAL_CODE_MIN_LENGTH = 2
MANUAL_CODE_MAX_LENGTH = 50


@dataclass
class ManualCodeResult:
    """Result of manual code validation with policy enforcement.

    Attributes:
        code: The validated/generated code string.
        was_auto_generated: True if user code was discarded and auto-generated instead.
    """
    code: str
    was_auto_generated: bool = False


def normalize_item_type(value: str | None) -> str:
    key = str(value or "raw").strip().replace(" ", "_")
    return ITEM_TYPE_PREFIX.get(key, ITEM_TYPE_PREFIX.get(key.lower(), "RM"))


def normalize_item_code(value: str) -> str:
    normalized = " ".join(str(value or "").split()).strip().upper()
    if not normalized:
        raise ValueError("Item code is required.")
    if len(normalized) > 50:
        raise ValueError("Item code must be at most 50 characters.")
    return normalized


def normalize_category_prefix(value: str | None, *, fallback_name: str = "GEN") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", str(value or "").upper())
    if not cleaned:
        cleaned = re.sub(r"[^A-Za-z0-9]", "", fallback_name.upper())
    return (cleaned or "GEN")[:10]


class ItemCodeService:
    """Tenant-scoped item code generation backed by an atomic sequence table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit_service = NumberSeriesAuditService(session)

    async def validate_manual_code(
        self,
        *,
        tenant_id: uuid.UUID,
        code: str,
        target: str,
    ) -> str:
        normalized = normalize_item_code(code)
        if await self.code_exists(tenant_id=tenant_id, code=normalized, target=target):
            raise ValueError(f"Item code '{normalized}' already exists in this tenant.")
        return normalized

    async def validate_manual_code_with_policy(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
        code: str,
        user_is_admin: bool = False,
        sub_type: str = "",
        entity_name: str = "",
        user_id: Optional[uuid.UUID] = None,
        entity_id: Optional[uuid.UUID] = None,
    ) -> ManualCodeResult:
        """Validate a user-provided manual code against the override policy.

        This method enforces the manual_override policy from the NumberSeriesConfig:
        - "never": Discards the user code silently and auto-generates instead.
        - "admin_only": Rejects non-admin users with an error; accepts admin users.
        - "always": Accepts any authenticated user's code.

        When the policy permits a manual code, validates:
        - Format: alphanumeric + hyphens + underscores only, 2–50 characters.
        - Uniqueness: within tenant + entity_type.

        If no config exists, defaults to "never" (auto-generate for all users).

        Args:
            tenant_id: The tenant UUID.
            entity_type: Entity type (material, purchase_order, etc.).
            code: The user-provided manual code.
            user_is_admin: Whether the requesting user has admin privileges.
            sub_type: Sub-type for prefix lookup if auto-generation is needed.
            entity_name: Entity name used for abbreviation if auto-generation is needed.
            user_id: The acting user's UUID (for audit logging).
            entity_id: The entity ID the code is assigned to (for audit logging).

        Returns:
            ManualCodeResult with the validated code or auto-generated code.

        Raises:
            ValueError: If the policy rejects the user (admin_only for non-admin),
                        or if the code format is invalid, or if a duplicate is found.
        """
        config = await self._try_load_config(tenant_id=tenant_id, entity_type=entity_type)

        # Determine the override policy. Default to "never" if no config.
        policy = config.manual_override if config else "never"

        # Policy: "never" — discard user code, auto-generate instead (no error)
        if policy == "never":
            generated_code = await self.generate_for_entity(
                tenant_id=tenant_id,
                entity_type=entity_type,
                sub_type=sub_type,
                entity_name=entity_name,
                user_id=user_id,
                entity_id=entity_id,
            )
            return ManualCodeResult(code=generated_code, was_auto_generated=True)

        # Policy: "admin_only" — reject non-admin users with error
        if policy == "admin_only" and not user_is_admin:
            raise ValueError(
                "Manual code entry is restricted to administrators. "
                "Contact your system administrator or use auto-generated codes."
            )

        # Policy: "always" OR ("admin_only" AND user is admin) — accept the code
        # Validate format: alphanumeric + hyphens + underscores only
        stripped_code = code.strip()
        if len(stripped_code) < MANUAL_CODE_MIN_LENGTH:
            raise ValueError(
                f"Manual code must be at least {MANUAL_CODE_MIN_LENGTH} characters long."
            )
        if len(stripped_code) > MANUAL_CODE_MAX_LENGTH:
            raise ValueError(
                f"Manual code must be at most {MANUAL_CODE_MAX_LENGTH} characters long."
            )
        if not MANUAL_CODE_PATTERN.match(stripped_code):
            raise ValueError(
                "Manual code may only contain alphanumeric characters, hyphens, and underscores."
            )

        # Validate uniqueness within tenant + entity_type
        target = "material" if entity_type == "material" else entity_type
        conflicting_entity = await self._find_entity_with_code(
            tenant_id=tenant_id, code=stripped_code, target=target
        )
        if conflicting_entity is not None:
            entity_id_found, entity_name_found = conflicting_entity
            raise ValueError(
                f"Code '{stripped_code}' is already in use by "
                f"'{entity_name_found}' (ID: {entity_id_found})."
            )

        # Log audit event for manual override (Requirement 13.2)
        if user_id is not None:
            try:
                await self._audit_service.log_manual_override(
                    tenant_id=tenant_id,
                    entity_type=entity_type,
                    generated_code=stripped_code,
                    user_id=user_id,
                    entity_id=entity_id,
                    metadata={
                        "sub_type": sub_type,
                        "entity_name": entity_name,
                        "user_is_admin": user_is_admin,
                    } if (sub_type or entity_name) else None,
                )
            except Exception as e:
                logger.warning(
                    "Failed to log audit for manual override: %s", e
                )

        return ManualCodeResult(code=stripped_code, was_auto_generated=False)

    async def _try_load_config(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
    ) -> Optional[NumberSeriesConfigModel]:
        """Try to load an existing NumberSeriesConfig without creating one.

        Returns None if no config row exists for this tenant+entity_type.
        """
        return await self._session.scalar(
            select(NumberSeriesConfigModel).where(
                NumberSeriesConfigModel.tenant_id == tenant_id,
                NumberSeriesConfigModel.entity_type == entity_type,
            )
        )

    async def _find_entity_with_code(
        self,
        *,
        tenant_id: uuid.UUID,
        code: str,
        target: str,
    ) -> Optional[tuple[uuid.UUID, str]]:
        """Find an existing entity with the given code.

        Returns a tuple of (entity_id, entity_name) if a conflict is found,
        or None if the code is available.
        """
        if target == "material":
            model = MaterialModel
        elif target == "customer":
            model = ClientModel
        else:
            model = ItemTemplateModel
        normalized = code.strip().upper()
        stmt = select(model.id, model.name).where(
            model.tenant_id == tenant_id,
            func.upper(model.code) == normalized,
            model.is_deleted.is_(False),
        )
        row = (await self._session.execute(stmt)).first()
        if row is not None:
            return (row[0], row[1])
        return None

    async def generate(
        self,
        *,
        tenant_id: uuid.UUID,
        item_type: str,
        category_id: uuid.UUID,
        target: str,
    ) -> str:
        category = await self._session.scalar(
            select(MaterialCategoryModel).where(
                MaterialCategoryModel.id == category_id,
                MaterialCategoryModel.tenant_id == tenant_id,
                MaterialCategoryModel.is_deleted.is_(False),
            )
        )
        if category is None:
            raise ValueError("Category is required for item code generation.")

        type_prefix = normalize_item_type(item_type)
        category_prefix = normalize_category_prefix(category.code_prefix, fallback_name=category.name)
        if category.code_prefix != category_prefix:
            category.code_prefix = category_prefix

        sequence = await self._session.scalar(
            select(ItemCodeSequenceModel)
            .where(
                ItemCodeSequenceModel.tenant_id == tenant_id,
                ItemCodeSequenceModel.item_type == type_prefix,
                ItemCodeSequenceModel.category_id == category_id,
            )
            .with_for_update()
        )
        if sequence is None:
            sequence = ItemCodeSequenceModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                item_type=type_prefix,
                category_id=category_id,
                next_number=await self._initial_next_number(
                    tenant_id=tenant_id,
                    type_prefix=type_prefix,
                    category_prefix=category_prefix,
                    target=target,
                ),
            )
            self._session.add(sequence)
            await self._session.flush()

        while True:
            candidate = f"{type_prefix}-{category_prefix}-{sequence.next_number:04d}"
            sequence.next_number += 1
            if not await self.code_exists(tenant_id=tenant_id, code=candidate, target=target):
                return candidate

    async def code_exists(self, *, tenant_id: uuid.UUID, code: str, target: str) -> bool:
        if target == "material":
            model = MaterialModel
        elif target == "customer":
            model = ClientModel
        else:
            model = ItemTemplateModel
        stmt = select(model.id).where(
            model.tenant_id == tenant_id,
            func.upper(model.code) == normalize_item_code(code),
            model.is_deleted.is_(False),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def _initial_next_number(
        self,
        *,
        tenant_id: uuid.UUID,
        type_prefix: str,
        category_prefix: str,
        target: str,
    ) -> int:
        if target == "material":
            model = MaterialModel
        elif target == "customer":
            model = ClientModel
        else:
            model = ItemTemplateModel
        like_prefix = f"{type_prefix}-{category_prefix}-"
        rows = (
            await self._session.execute(
                select(model.code).where(
                    model.tenant_id == tenant_id,
                    model.code.ilike(f"{like_prefix}%"),
                    model.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        max_seen = 0
        for code in rows:
            suffix = str(code).replace(like_prefix, "", 1)
            if suffix.isdigit():
                max_seen = max(max_seen, int(suffix))
        return max_seen + 1

    # ══════════════════════════════════════════════════════════════════════
    # Number Series Engine — New Generic API
    # ══════════════════════════════════════════════════════════════════════

    async def generate_for_entity(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
        sub_type: str = "",
        entity_name: str = "",
        user_id: Optional[uuid.UUID] = None,
        entity_id: Optional[uuid.UUID] = None,
    ) -> str:
        """Generate a code using the Number Series Engine.

        If a NumberSeriesConfig exists for the tenant+entity_type and auto_generate=True,
        uses the new format: {prefix}{sep}{abbrev}{sep}{seq} (or {prefix}{sep}{seq}).
        If no config exists, falls back to legacy format for materials.

        Args:
            tenant_id: The tenant UUID.
            entity_type: Entity type (material, purchase_order, etc.)
            sub_type: Sub-type for prefix lookup (e.g. "raw", "finished" for materials).
            entity_name: Entity name used for abbreviation generation.
            user_id: The acting user's UUID (for audit logging).
            entity_id: The entity ID the code is being generated for (for audit logging).

        Returns:
            A unique generated code string.

        Raises:
            ValueError: If auto_generate is disabled, sub_type has no mapping, or
                        max retries exceeded.
        """
        config = await self.get_or_create_config(tenant_id=tenant_id, entity_type=entity_type)

        if not config.auto_generate:
            raise ValueError(
                f"Auto-generation is disabled for '{entity_type}'. A manual code is required."
            )

        # Resolve prefix: use sub-type prefix if sub_type is provided, else config.prefix
        if sub_type:
            prefix = await self._resolve_prefix(tenant_id, entity_type, sub_type)
        else:
            prefix = config.prefix or entity_type.upper()[:3]

        # Generate abbreviation segment if enabled
        middle = ""
        if config.include_abbreviation and entity_name:
            middle = self._generate_abbreviation(entity_name, config.abbreviation_length)

        # Acquire sequence with row-level lock
        sequence = await self._get_or_create_sequence(tenant_id, entity_type, prefix)

        # Determine the target model for uniqueness check
        target = "material" if entity_type == "material" else entity_type

        # Generate unique code with retry loop
        for _ in range(MAX_GENERATION_ATTEMPTS):
            seq_str = str(sequence.next_number).zfill(config.sequence_length)
            if middle:
                candidate = f"{prefix}{config.separator}{middle}{config.separator}{seq_str}"
            else:
                candidate = f"{prefix}{config.separator}{seq_str}"
            sequence.next_number += 1

            if not await self.code_exists(tenant_id=tenant_id, code=candidate, target=target):
                # Log audit event for code generation (Requirement 13.1)
                if user_id is not None:
                    try:
                        await self._audit_service.log_generated(
                            tenant_id=tenant_id,
                            entity_type=entity_type,
                            generated_code=candidate,
                            user_id=user_id,
                            entity_id=entity_id,
                            metadata={
                                "sub_type": sub_type,
                                "entity_name": entity_name,
                            } if (sub_type or entity_name) else None,
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to log audit for code generation: %s", e
                        )
                return candidate

        raise ValueError(
            f"Failed to generate a unique code for entity_type='{entity_type}' "
            f"after {MAX_GENERATION_ATTEMPTS} attempts."
        )

    async def get_or_create_config(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
    ) -> NumberSeriesConfigModel:
        """Load config for entity_type, creating defaults if not exists.

        On first access for a tenant+entity_type, seeds a default config row.
        Also seeds default prefix mappings for 'material' entity type.
        """
        config = await self._session.scalar(
            select(NumberSeriesConfigModel).where(
                NumberSeriesConfigModel.tenant_id == tenant_id,
                NumberSeriesConfigModel.entity_type == entity_type,
            )
        )

        if config is not None:
            return config

        # Create default config
        defaults = DEFAULT_ENTITY_CONFIGS.get(entity_type, {
            "auto_generate": True,
            "prefix": entity_type.upper()[:3],
            "include_abbreviation": False,
            "manual_override": "never",
        })

        now = datetime.now(timezone.utc)
        config = NumberSeriesConfigModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            entity_type=entity_type,
            auto_generate=defaults["auto_generate"],
            manual_override=defaults["manual_override"],
            prefix=defaults["prefix"],
            include_abbreviation=defaults["include_abbreviation"],
            abbreviation_length=3,
            sequence_length=6,
            separator="-",
            lock_after_save=True,
            created_at=now,
            updated_at=now,
        )
        self._session.add(config)

        # Seed default prefix mappings for material entity type
        if entity_type == "material":
            await self._seed_default_prefixes(tenant_id, entity_type)

        await self._session.flush()
        return config

    async def _seed_default_prefixes(
        self, tenant_id: uuid.UUID, entity_type: str
    ) -> None:
        """Seed default sub-type prefix mappings if none exist for this tenant+entity."""
        existing = await self._session.scalar(
            select(NumberSeriesPrefixModel.id).where(
                NumberSeriesPrefixModel.tenant_id == tenant_id,
                NumberSeriesPrefixModel.entity_type == entity_type,
            ).limit(1)
        )
        if existing is not None:
            return  # Already seeded

        now = datetime.now(timezone.utc)
        for sub_type, prefix in DEFAULT_MATERIAL_PREFIXES.items():
            self._session.add(NumberSeriesPrefixModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                entity_type=entity_type,
                sub_type=sub_type,
                prefix=prefix,
                is_active=True,
                created_at=now,
                updated_at=now,
            ))

    async def _resolve_prefix(
        self, tenant_id: uuid.UUID, entity_type: str, sub_type: str
    ) -> str:
        """Look up sub-type prefix from NumberSeriesPrefixModel.

        Falls back to ITEM_TYPE_PREFIX dict for backward compatibility if
        no NumberSeriesPrefixModel row exists and entity_type is 'material'.

        Raises:
            ValueError: If no prefix mapping is found for the sub_type.
        """
        # Normalize sub_type for lookup
        normalized_sub_type = sub_type.strip().lower().replace("-", "_").replace(" ", "_")

        prefix_row = await self._session.scalar(
            select(NumberSeriesPrefixModel).where(
                NumberSeriesPrefixModel.tenant_id == tenant_id,
                NumberSeriesPrefixModel.entity_type == entity_type,
                NumberSeriesPrefixModel.sub_type == normalized_sub_type,
                NumberSeriesPrefixModel.is_active.is_(True),
            )
        )

        if prefix_row is not None:
            return prefix_row.prefix

        # Fallback for material entity using legacy ITEM_TYPE_PREFIX dict
        if entity_type == "material":
            legacy_prefix = ITEM_TYPE_PREFIX.get(normalized_sub_type) or ITEM_TYPE_PREFIX.get(sub_type)
            if legacy_prefix:
                return legacy_prefix

        raise ValueError(
            f"No prefix mapping found for entity_type='{entity_type}', "
            f"sub_type='{sub_type}'. Configure it in Settings → Number Series."
        )

    async def _get_or_create_sequence(
        self, tenant_id: uuid.UUID, entity_type: str, prefix: str
    ) -> NumberSeriesSequenceModel:
        """Acquire or create a sequence row with SELECT FOR UPDATE row-level locking.

        This ensures no two concurrent requests receive the same sequence number.
        """
        sequence = await self._session.scalar(
            select(NumberSeriesSequenceModel)
            .where(
                NumberSeriesSequenceModel.tenant_id == tenant_id,
                NumberSeriesSequenceModel.entity_type == entity_type,
                NumberSeriesSequenceModel.prefix == prefix,
            )
            .with_for_update()
        )

        if sequence is not None:
            return sequence

        # Create new sequence starting at 1
        now = datetime.now(timezone.utc)
        sequence = NumberSeriesSequenceModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            entity_type=entity_type,
            prefix=prefix,
            next_number=1,
            created_at=now,
            updated_at=now,
        )
        self._session.add(sequence)
        await self._session.flush()
        return sequence

    async def format_preview(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
        sub_type: str = "",
        entity_name: str = "",
    ) -> tuple[str, str]:
        """Preview the generated code format without incrementing the sequence.

        Returns a tuple of (preview_code, format_pattern).
        Uses placeholder sequence number for display purposes only.
        """
        config = await self.get_or_create_config(tenant_id=tenant_id, entity_type=entity_type)

        # Resolve prefix
        if sub_type:
            try:
                prefix = await self._resolve_prefix(tenant_id, entity_type, sub_type)
            except ValueError:
                prefix = sub_type.upper()[:3]
        else:
            prefix = config.prefix or entity_type.upper()[:3]

        # Generate abbreviation segment for preview
        middle = ""
        if config.include_abbreviation and entity_name:
            middle = self._generate_abbreviation(entity_name, config.abbreviation_length)
        elif config.include_abbreviation:
            middle = "X" * config.abbreviation_length

        # Use a sample sequence number for preview
        seq_str = "0" * config.sequence_length

        if middle:
            preview = f"{prefix}{config.separator}{middle}{config.separator}{seq_str}"
            pattern = f"{{prefix}}{config.separator}{{abbreviation}}{config.separator}{{sequence:{config.sequence_length}d}}"
        else:
            preview = f"{prefix}{config.separator}{seq_str}"
            pattern = f"{{prefix}}{config.separator}{{sequence:{config.sequence_length}d}}"

        return preview, pattern

    async def log_config_change(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
        old_value: str,
        new_value: str,
        user_id: uuid.UUID,
        metadata: Optional[dict] = None,
    ) -> uuid.UUID:
        """Log a configuration change event to the audit trail.

        Requirement 13.3: Record event_type "config_changed" with old_value and
        new_value when an administrator updates Number Series configuration.

        This is a convenience method that delegates to NumberSeriesAuditService.
        Intended to be called by the Number Series API routes on config updates.

        Args:
            tenant_id: The tenant UUID.
            entity_type: Entity type whose config was changed.
            old_value: JSON string representing previous configuration.
            new_value: JSON string representing new configuration.
            user_id: The administrator who made the change.
            metadata: Optional additional context.

        Returns:
            The UUID of the created audit log entry.
        """
        return await self._audit_service.log_config_changed(
            tenant_id=tenant_id,
            entity_type=entity_type,
            old_value=old_value,
            new_value=new_value,
            user_id=user_id,
            metadata=metadata,
        )

    @staticmethod
    def _generate_abbreviation(name: str, length: int = 3) -> str:
        """Generate a deterministic abbreviation from an entity name.

        Rules:
        - Remove special characters, split into words, uppercase
        - Single word: take first N characters
        - Multiple words: take first character of each word, pad from longest word if needed
        - Always exactly `length` characters, padded with 'X' if necessary
        - Deterministic: same input always produces same output

        Args:
            name: The entity name to abbreviate.
            length: Desired abbreviation length (default 3).

        Returns:
            An uppercase string of exactly `length` characters.
        """
        cleaned = re.sub(r'[^A-Za-z0-9\s]', '', name)
        words = cleaned.upper().split()

        if not words:
            return "GEN"[:length].ljust(length, "X")

        if len(words) == 1:
            return words[0][:length].ljust(length, "X")

        # Multiple words: first char of each word
        abbrev = "".join(w[0] for w in words if w)
        if len(abbrev) >= length:
            return abbrev[:length]

        # Pad from the longest word's remaining characters
        longest_word = max(words, key=len)
        remaining_needed = length - len(abbrev)
        abbrev += longest_word[1:remaining_needed + 1]

        return abbrev[:length].ljust(length, "X")
