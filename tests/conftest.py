"""
Root conftest for the tests/ tree.

Ensures the repository root is on sys.path and patches PostgreSQL-specific
dialect types so models can be imported against SQLite for testing.
"""
from __future__ import annotations

import os
import sys

# Ensure repository root is on sys.path.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Patch PostgreSQL JSONB → generic JSON so SQLite can compile models.
try:
    from sqlalchemy import JSON as _SA_JSON
    from sqlalchemy.dialects import postgresql as _pg
    _pg.JSONB = _SA_JSON  # type: ignore[attr-defined]
except Exception:
    pass
