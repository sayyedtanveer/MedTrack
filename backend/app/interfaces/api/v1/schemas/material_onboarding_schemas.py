from pydantic import BaseModel
from typing import Any
class MappingRequest(BaseModel):
    name: str | None = None
    mapping: dict[str,str]
class ProfileRequest(BaseModel):
    name: str
    defaults: dict[str,Any]
class ExecuteRequest(BaseModel):
    dry_run: bool = False
