"""Concurrency checks for the existing item code counter scopes."""
import asyncio
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable

from backend.app.application.inventory.services.item_code_service import ItemCodeService
from backend.app.infrastructure.persistence.models.item_code_sequence_model import ItemCodeSequenceModel
from backend.app.infrastructure.persistence.models.material_category_model import MaterialCategoryModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.number_series_models import (
    NumberSeriesConfigModel, NumberSeriesPrefixModel, NumberSeriesSequenceModel,
)
from backend.app.interfaces.api.v1.routes.number_series import get_code_entry_policy


@pytest.mark.parametrize("configured", [False, True], ids=["category-counter", "number-series"])
@pytest.mark.asyncio
async def test_new_counter_is_safe_under_concurrent_material_creation(configured):
    url = os.getenv("MEDTRACK_CODE_TEST_URL")
    if not url:
        pytest.skip("Requires disposable PostgreSQL")
    parsed = urlsplit(url)
    assert parsed.hostname == "127.0.0.1" and parsed.port == 55471
    assert parsed.path == "/medtrack_subcontract_disposable"
    schema = "item_code_" + uuid4().hex
    engine = create_async_engine(url)
    scoped_engine = engine.execution_options(schema_translate_map={None: schema})
    factory = async_sessionmaker(scoped_engine, expire_on_commit=False)
    tenant, other, category, other_category = [uuid4() for _ in range(4)]
    now = datetime.now(timezone.utc)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        async with scoped_engine.begin() as connection:
            for model in (MaterialCategoryModel, MaterialModel, ItemCodeSequenceModel,
                          NumberSeriesConfigModel, NumberSeriesPrefixModel, NumberSeriesSequenceModel):
                await connection.execute(CreateTable(model.__table__, include_foreign_key_constraints=[]))
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(container=SimpleNamespace(session_factory=factory))))
        policy = await get_code_entry_policy("material", request, tenant)
        assert policy.auto_generate and policy.manual_override == "never"
        async with factory() as session:
            assert await session.scalar(select(func.count()).select_from(NumberSeriesConfigModel)) == 0
            for scope, cat in ((tenant, category), (other, other_category)):
                session.add(MaterialCategoryModel(
                    id=cat, tenant_id=scope, name="Test material group", code_prefix="AL",
                    created_at=now, updated_at=now,
                ))
                if configured:
                    session.add(NumberSeriesConfigModel(
                        tenant_id=scope, entity_type="material", auto_generate=True,
                        manual_override="admin_only", sequence_length=3, separator="_",
                        include_abbreviation=False,
                    ))
                    session.add(NumberSeriesPrefixModel(
                        tenant_id=scope, entity_type="material", sub_type="raw", prefix="TX",
                    ))
            await session.commit()
        if configured:
            assert (await get_code_entry_policy("material", request, tenant)).manual_override == "admin_only"

        async def create(scope, cat, name):
            async with factory.begin() as session:
                service = ItemCodeService(session)
                if configured:
                    code = await service.generate_for_entity(tenant_id=scope, entity_type="material",
                                                            sub_type="raw", entity_name=name)
                else:
                    code = await service.generate(tenant_id=scope, item_type="raw", category_id=cat, target="material")
                session.add(MaterialModel(tenant_id=scope, name=name, code=code, material_type="raw"))
            return code

        codes = await asyncio.wait_for(asyncio.gather(
            create(tenant, category, "First material"),
            create(tenant, category, "Second material"),
            create(other, other_category, "Separate tenant material"),
        ), timeout=15)
        expected = ("TX_001", "TX_002") if configured else ("RM-AL-0001", "RM-AL-0002")
        assert set(codes[:2]) == set(expected)
        assert codes[2] == expected[0]
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()



@pytest.mark.asyncio
async def test_locked_material_keeps_code_on_type_change_and_rejects_edit():
    from unittest.mock import AsyncMock

    from backend.app.application.inventory.commands.inventory_commands import UpdateMaterialCommand
    from backend.app.application.inventory.handlers.inventory_handlers import UpdateMaterialHandler
    from backend.app.domain.inventory.entities.material import Material

    tenant_id, material_id = uuid4(), uuid4()
    material = Material(id=material_id, tenant_id=tenant_id, code="RM-AL-0099", name="Machined blank", material_type="raw")
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=material),
                           name_exists=AsyncMock(return_value=False), save=AsyncMock())
    uow = SimpleNamespace(session=SimpleNamespace(scalar=AsyncMock(return_value=0)), commit=AsyncMock())
    handler = UpdateMaterialHandler(repo, uow)
    with pytest.raises(ValueError, match="Item code is immutable"):
        await handler.handle(UpdateMaterialCommand(id=material_id, tenant_id=tenant_id, code="NEW-CODE"))
    repo.save.assert_not_awaited()
    await handler.handle(UpdateMaterialCommand(id=material_id, tenant_id=tenant_id, material_type="semi_finished"))
    assert material.code == "RM-AL-0099"
    assert material.material_type.value == "semi_finished"
    repo.save.assert_awaited_once_with(material)

