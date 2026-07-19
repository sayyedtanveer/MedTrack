from backend.app.domain.inventory.entities.material import MaterialType
from backend.app.infrastructure.persistence.repositories.material_repository import _normalize_material_type


def test_normalize_material_type_accepts_legacy_values():
    assert _normalize_material_type("RAW") == MaterialType.RAW
    assert _normalize_material_type("raw_material") == MaterialType.RAW
    assert _normalize_material_type("FG") == MaterialType.FINISHED
    assert _normalize_material_type("finished_goods") == MaterialType.FINISHED


def test_normalize_material_type_defaults_unknown_values_to_raw():
    assert _normalize_material_type(None) == MaterialType.RAW
    assert _normalize_material_type("unexpected") == MaterialType.RAW
