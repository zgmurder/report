from sqlalchemy.orm import Session

from app.repositories.catalog_repository import CatalogRepository
from app.schemas.catalog import DataSourceItem, ReportTemplateDetail, StatComponentItem


class CatalogService:
    def __init__(self, db: Session):
        self.repository = CatalogRepository(db)

    def list_templates(self) -> list[ReportTemplateDetail]:
        return [ReportTemplateDetail.model_validate(row, from_attributes=True) for row in self.repository.list_templates()]

    def list_components(self) -> list[StatComponentItem]:
        return [StatComponentItem.model_validate(row, from_attributes=True) for row in self.repository.list_components()]

    def list_data_sources(self) -> list[DataSourceItem]:
        return [DataSourceItem.model_validate(row, from_attributes=True) for row in self.repository.list_data_sources()]
