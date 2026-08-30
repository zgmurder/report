from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.repositories.catalog_repository import CatalogRepository
from app.services.template_file_service import TemplateFileService
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
        self.template_files = TemplateFileService()

    def list_templates(self) -> list[ReportTemplateDetail]:
        return [ReportTemplateDetail.model_validate(row, from_attributes=True) for row in self.repository.list_templates()]

    def create_template(self, req: ReportTemplateCreateRequest) -> ReportTemplateDetail:
        data = req.model_dump(mode="json")
        data["name"] = self._require_text(req.name, "模板名称不能为空")
        row = self.repository.create_template(data)
        return ReportTemplateDetail.model_validate(row, from_attributes=True)

    async def upload_template(
        self,
        file: UploadFile,
        name: str | None = None,
        category: str = "daily",
        description: str = "",
        status_value: str = "enabled",
    ) -> ReportTemplateDetail:
        file_data = await self.template_files.save_word(file)
        template_name = self._require_text(name or Path(str(file_data["original_filename"])).stem, "模板名称不能为空")
        try:
            row = self.repository.create_template({
                "name": template_name,
                "category": self._require_text(category, "模板分类不能为空"),
                "description": description.strip(),
                "content_json": {},
                "status": self._require_text(status_value, "模板状态不能为空"),
                **file_data,
            })
        except Exception:
            self.template_files.delete(str(file_data["file_path"]))
            raise
        return ReportTemplateDetail.model_validate(row, from_attributes=True)

    def update_template(self, template_id: int, req: ReportTemplateUpdateRequest) -> ReportTemplateDetail:
        data = req.model_dump(exclude_unset=True, mode="json")
        if req.name is not None:
            data["name"] = self._require_text(req.name, "模板名称不能为空")
        row = self.repository.update_template(template_id, data)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
        return ReportTemplateDetail.model_validate(row, from_attributes=True)

    def download_template(self, template_id: int) -> tuple[str, str, bytes]:
        row = self.repository.get_template(template_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
        content = self.template_files.read(row.file_path)
        filename = row.original_filename or f"{row.name}.docx"
        return filename, row.mime_type or "application/octet-stream", content

    def get_template_content(self, template_id: int) -> dict[str, str | int]:
        row = self.repository.get_template(template_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
        return {
            "id": row.id,
            "name": row.name,
            "original_filename": row.original_filename or "",
            "html": self.template_files.extract_html(row.file_path),
        }

    def delete_template(self, template_id: int) -> dict[str, bool]:
        row = self.repository.delete_template(template_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
        self.template_files.delete(row.file_path)
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

    @staticmethod
    def _require_text(value: str, message: str) -> str:
        text = value.strip()
        if not text:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)
        return text
