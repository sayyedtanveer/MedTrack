import uuid
import pytest
from decimal import Decimal

from backend.app.application.product.commands.product_commands import CreateItemVariantCommand
from backend.app.application.product.handlers.product_handlers import CreateItemVariantHandler
from backend.app.domain.product.entities.item_template import ItemTemplate
from backend.app.domain.inventory.entities.material import Material, MaterialType
from backend.app.domain.product.value_objects.product_status import ProductStatus

# Mocks
class FakeUnitOfWork:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


class FakeTemplateRepo:
    def __init__(self, template):
        self.template = template

    async def get_by_id(self, id, tenant_id):
        return self.template


class FakeVariantRepo:
    def __init__(self):
        self.saved_variants = []

    async def get_by_variant_key(self, variant_key, template_id, tenant_id):
        return None

    async def save(self, variant):
        self.saved_variants.append(variant)


class FakeMaterialRepo:
    def __init__(self, should_fail=False):
        self.saved_materials = []
        self.should_fail = should_fail

    async def save(self, material):
        if self.should_fail:
            raise ValueError("Simulated DB failure")
        self.saved_materials.append(material)


class FakeItemCodeService:
    async def _try_load_config(self, tenant_id, entity_type):
        return None

    async def generate(self, tenant_id, item_type, category_id, target):
        return f"GEN-{uuid.uuid4().hex[:6]}"


@pytest.mark.asyncio
async def test_atomic_provisioning_success():
    """Test that a Material is automatically created and linked to a new Variant."""
    tenant_id = uuid.uuid4()
    template_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    base_unit = uuid.uuid4()

    template = ItemTemplate(
        id=template_id,
        tenant_id=tenant_id,
        code="TSHIRT",
        name="T-Shirt",
        attributes=[{"key": "Size", "values": ["S", "M", "L"]}],
        category_id=cat_id,
        base_unit_id=base_unit,
        status=ProductStatus.ACTIVE,
    )

    t_repo = FakeTemplateRepo(template)
    v_repo = FakeVariantRepo()
    m_repo = FakeMaterialRepo()
    uow = FakeUnitOfWork()
    code_svc = FakeItemCodeService()

    handler = CreateItemVariantHandler(
        template_repo=t_repo,
        variant_repo=v_repo,
        uow=uow,
        material_repo=m_repo,
        item_code_service=code_svc,
    )

    cmd = CreateItemVariantCommand(
        tenant_id=tenant_id,
        template_id=template_id,
        created_by=uuid.uuid4(),
        attribute_values={"Size": "M"},
        base_unit_id=None,
        material_id=None,
        standard_cost=Decimal("10"),
    )

    result = await handler.handle(cmd)

    # Assertions
    assert uow.committed is True
    assert len(m_repo.saved_materials) == 1
    assert len(v_repo.saved_variants) == 1

    material = m_repo.saved_materials[0]
    variant = v_repo.saved_variants[0]

    assert variant.material_id == material.id
    assert material.material_type == MaterialType.FINISHED
    assert material.tenant_id == tenant_id
    assert material.category_id == cat_id
    assert material.base_unit_id == base_unit
    assert material.name == variant.name


@pytest.mark.asyncio
async def test_atomic_provisioning_material_failure():
    """Test that if Material creation fails, the transaction is safely aborted before UOW commit."""
    tenant_id = uuid.uuid4()
    template = ItemTemplate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code="TSHIRT",
        name="T-Shirt",
        attributes=[{"key": "Size", "values": ["S"]}],
    )

    t_repo = FakeTemplateRepo(template)
    v_repo = FakeVariantRepo()
    m_repo = FakeMaterialRepo(should_fail=True)  # Will raise ValueError on save
    uow = FakeUnitOfWork()

    handler = CreateItemVariantHandler(
        template_repo=t_repo,
        variant_repo=v_repo,
        uow=uow,
        material_repo=m_repo,
    )

    cmd = CreateItemVariantCommand(
        tenant_id=tenant_id,
        template_id=template.id,
        created_by=uuid.uuid4(),
        attribute_values={"Size": "S"},
    )

    with pytest.raises(ValueError, match="Simulated DB failure"):
        await handler.handle(cmd)

    # UOW should not be committed because of the exception
    assert uow.committed is False


@pytest.mark.asyncio
async def test_existing_material_not_overwritten():
    """Test that if a variant is explicitly linked to an existing material, a new one is not created."""
    tenant_id = uuid.uuid4()
    template = ItemTemplate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code="TSHIRT",
        name="T-Shirt",
        attributes=[{"key": "Size", "values": ["L"]}],
    )

    t_repo = FakeTemplateRepo(template)
    v_repo = FakeVariantRepo()
    m_repo = FakeMaterialRepo()
    uow = FakeUnitOfWork()

    handler = CreateItemVariantHandler(
        template_repo=t_repo,
        variant_repo=v_repo,
        uow=uow,
        material_repo=m_repo,
    )

    existing_material_id = uuid.uuid4()
    cmd = CreateItemVariantCommand(
        tenant_id=tenant_id,
        template_id=template.id,
        created_by=uuid.uuid4(),
        attribute_values={"Size": "L"},
        material_id=existing_material_id,
    )

    result = await handler.handle(cmd)

    assert uow.committed is True
    assert len(m_repo.saved_materials) == 0  # No new material was provisioned
    assert len(v_repo.saved_variants) == 1
    assert v_repo.saved_variants[0].material_id == existing_material_id
