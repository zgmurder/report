from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.catalog_repository import CatalogRepository
from app.schemas.catalog import (
    DataSourceCreateRequest,
    DataSourceItem,
    DataSourceUpdateRequest,
    ReportTemplateCreateRequest,
    ReportTemplateDetail,
    ReportTemplateUpdateRequest,
    StatComponentCreateRequest,
    StatComponentItem,
    StatComponentUpdateRequest,
)


class CatalogService:
    def __init__(self, db: Session):
        self.repository = CatalogRepository(db)

    def list_templates(self) -> list[ReportTemplateDetail]:
        return [ReportTemplateDetail.model_validate(row, from_attributes=True) for row in self.repository.list_templates()]

    def create_template(self, req: ReportTemplateCreateRequest) -> ReportTemplateDetail:
        row = self.repository.create_template(req.model_dump(mode="json"))
        return ReportTemplateDetail.model_validate(row, from_attributes=True)

    def update_template(self, template_id: int, req: ReportTemplateUpdateRequest) -> ReportTemplateDetail:
        row = self.repository.update_template(template_id, req.model_dump(exclude_unset=True, mode="json"))
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
        return ReportTemplateDetail.model_validate(row, from_attributes=True)

    def delete_template(self, template_id: int) -> dict[str, bool]:
        deleted = self.repository.delete_template(template_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
        return {"deleted": True}

    def list_components(self) -> list[StatComponentItem]:
        return [StatComponentItem.model_validate(row, from_attributes=True) for row in self.repository.list_components()]

    def create_component(self, req: StatComponentCreateRequest) -> StatComponentItem:
        row = self.repository.create_component(req.model_dump(mode="json"))
        return StatComponentItem.model_validate(row, from_attributes=True)

    def update_component(self, component_id: int, req: StatComponentUpdateRequest) -> StatComponentItem:
        row = self.repository.update_component(component_id, req.model_dump(exclude_unset=True, mode="json"))
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="组件不存在")
        return StatComponentItem.model_validate(row, from_attributes=True)

    def delete_component(self, component_id: int) -> dict[str, bool]:
        deleted = self.repository.delete_component(component_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="组件不存在")
        return {"deleted": True}

    def list_data_sources(self) -> list[DataSourceItem]:
        return [DataSourceItem.model_validate(row, from_attributes=True) for row in self.repository.list_data_sources()]

    def create_data_source(self, req: DataSourceCreateRequest) -> DataSourceItem:
        row = self.repository.create_data_source(req.model_dump(mode="json"))
        return DataSourceItem.model_validate(row, from_attributes=True)

    def update_data_source(self, data_source_id: int, req: DataSourceUpdateRequest) -> DataSourceItem:
        row = self.repository.update_data_source(data_source_id, req.model_dump(exclude_unset=True, mode="json"))
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")
        return DataSourceItem.model_validate(row, from_attributes=True)

    def delete_data_source(self, data_source_id: int) -> dict[str, bool]:
        deleted = self.repository.delete_data_source(data_source_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")
        return {"deleted": True}
