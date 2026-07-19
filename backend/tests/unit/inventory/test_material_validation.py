import pytest

from backend.app.domain.inventory.entities.material import Material, MaterialType


def test_validate_name_for_type_rejects_generic_raw_material_names():
    with pytest.raises(ValueError, match="specific raw material name"):
        Material.validate_name_for_type("Raw Material", MaterialType.RAW)


def test_validate_name_for_type_accepts_specific_raw_material_names():
    Material.validate_name_for_type("Brass Body", MaterialType.RAW)


def test_validate_name_for_type_rejects_generic_finished_good_names():
    with pytest.raises(ValueError, match="specific finished good name"):
        Material.validate_name_for_type("Product", MaterialType.FINISHED)
