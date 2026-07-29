from __future__ import annotations

from dataclasses import dataclass, field
import uuid
from typing import Optional

from backend.app.application.shared.command import Command


@dataclass
class ApproveTenantCommand(Command):
    acted_by: Optional[uuid.UUID] = None


@dataclass
class RejectTenantCommand(Command):
    reason: str = ""
    acted_by: Optional[uuid.UUID] = None


@dataclass
class SuspendTenantCommand(Command):
    reason: str = ""
    acted_by: Optional[uuid.UUID] = None


@dataclass
class ReactivateTenantCommand(Command):
    acted_by: Optional[uuid.UUID] = None
