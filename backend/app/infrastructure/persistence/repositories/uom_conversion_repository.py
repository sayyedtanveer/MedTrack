from typing import Type

from backend.app.domain.inventory.entities.uom_conversion import UomConversion
from backend.app.infrastructure.persistence.models.uom_conversion_model import UomConversionModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository

class UomConversionRepository(BaseRepository[UomConversion, UomConversionModel]):
    def _model_class(self) -> Type[UomConversionModel]:
        return UomConversionModel

    def _to_entity(self, model: UomConversionModel) -> UomConversion:
        entity = UomConversion(
            id=model.id,
            tenant_id=model.tenant_id,
            from_uom_id=model.from_uom_id,
            to_uom_id=model.to_uom_id,
            multiply_by=model.conversion_factor,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        entity._is_deleted = model.is_deleted
        entity._deleted_at = model.deleted_at
        return entity

    def _to_model(self, entity: UomConversion) -> UomConversionModel:
        return UomConversionModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            from_uom_id=entity.from_uom_id,
            to_uom_id=entity.to_uom_id,
            conversion_factor=entity.multiply_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
        )
