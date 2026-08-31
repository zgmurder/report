from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, is_admin
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


SECRET_PLACEHOLDER = "[REDACTED]"
SECRET_KEY_MARKERS = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "credential",
)


class CatalogService:
    def __init__(self, db: Session, current_user: CurrentUser):
        self.repository = CatalogRepository(db)
        self.template_files = TemplateFileService()
        self.current_user = current_user

    def list_templates(self) -> list[ReportTemplateDetail]:
        return [
            ReportTemplateDetail.model_validate(row, from_attributes=True)
            for row in self.repository.list_templates(self.current_user.id)
        ]

    def create_template(self, req: ReportTemplateCreateRequest) -> ReportTemplateDetail:
        data = req.model_dump(mode="json")
        data["name"] = self._require_text(req.name, "模板名称不能为空")
        data["category"] = "default"
        data["created_by"] = self.current_user.id
        row = self.repository.create_template(data)
        return ReportTemplateDetail.model_validate(row, from_attributes=True)

    async def upload_template(
        self,
        file: UploadFile,
        name: str | None = None,
        description: str = "",
        status_value: str = "enabled",
    ) -> ReportTemplateDetail:
        file_data = await self.template_files.save_word(file)
        template_name = self._require_text(name or Path(str(file_data["original_filename"])).stem, "模板名称不能为空")
        try:
            row = self.repository.create_template({
                "name": template_name,
                "category": "default",
                "description": description.strip(),
                "content_json": {},
                "status": self._require_text(status_value, "模板状态不能为空"),
                "created_by": self.current_user.id,
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
        row = self.repository.update_template(template_id, self.current_user.id, data)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
        return ReportTemplateDetail.model_validate(row, from_attributes=True)

    def download_template(self, template_id: int) -> tuple[str, str, bytes]:
        row = self.repository.get_template(template_id, self.current_user.id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
        content = self.template_files.read(row.file_path)
        filename = row.original_filename or f"{row.name}.docx"
        return filename, row.mime_type or "application/octet-stream", content

    def get_template_content(self, template_id: int) -> dict[str, str | int]:
        row = self.repository.get_template(template_id, self.current_user.id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
        return {
            "id": row.id,
            "name": row.name,
            "original_filename": row.original_filename or "",
            "html": self.template_files.extract_html(row.file_path),
        }

    def delete_template(self, template_id: int) -> dict[str, bool]:
        row = self.repository.get_template(template_id, self.current_user.id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
        receipt = self.template_files.recycle(row.file_path)
        try:
            deleted = self.repository.delete_template(template_id, self.current_user.id)
        except Exception:
            self.template_files.restore_recycled(receipt)
            raise
        if not deleted:
            self.template_files.restore_recycled(receipt)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
        self.template_files.purge_recycled(receipt)
        return {"deleted": True}

    def list_components(self) -> list[StatComponentItem]:
        return [StatComponentItem.model_validate(row, from_attributes=True) for row in self.repository.list_components()]

    def create_component(self, req: StatComponentCreateRequest) -> StatComponentItem:
        self._require_admin()
        row = self.repository.create_component(req.model_dump(mode="json"))
        return StatComponentItem.model_validate(row, from_attributes=True)

    def update_component(self, component_id: int, req: StatComponentUpdateRequest) -> StatComponentItem:
        self._require_admin()
        row = self.repository.update_component(component_id, req.model_dump(exclude_unset=True, mode="json"))
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="组件不存在")
        return StatComponentItem.model_validate(row, from_attributes=True)

    def delete_component(self, component_id: int) -> dict[str, bool]:
        self._require_admin()
        deleted = self.repository.delete_component(component_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="组件不存在")
        return {"deleted": True}

    def list_data_sources(self) -> list[DataSourceItem]:
        self._require_admin()
        return [self._data_source_item(row) for row in self.repository.list_data_sources()]

    def create_data_source(self, req: DataSourceCreateRequest) -> DataSourceItem:
        self._require_admin()
        row = self.repository.create_data_source(req.model_dump(mode="json"))
        return self._data_source_item(row)

    def update_data_source(self, data_source_id: int, req: DataSourceUpdateRequest) -> DataSourceItem:
        self._require_admin()
        data = req.model_dump(exclude_unset=True, mode="json")
        if "config_json" in data:
            existing = self.repository.get_data_source(data_source_id)
            if not existing:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")
            data["config_json"] = self._preserve_secret_placeholders(data["config_json"], existing.config_json)
        row = self.repository.update_data_source(data_source_id, data)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")
        return self._data_source_item(row)

    def delete_data_source(self, data_source_id: int) -> dict[str, bool]:
        self._require_admin()
        deleted = self.repository.delete_data_source(data_source_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")
        return {"deleted": True}

    def _require_admin(self) -> None:
        if not is_admin(self.current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    @classmethod
    def _data_source_item(cls, row) -> DataSourceItem:
        item = DataSourceItem.model_validate(row, from_attributes=True)
        return item.model_copy(update={"config_json": cls._redact_secrets(item.config_json)})

    @classmethod
    def _redact_secrets(cls, value, key: str | None = None):
        if key is not None and cls._is_secret_key(key):
            return SECRET_PLACEHOLDER
        if isinstance(value, dict):
            return {item_key: cls._redact_secrets(item, str(item_key)) for item_key, item in value.items()}
        if isinstance(value, list):
            return [cls._redact_secrets(item) for item in value]
        return value

    @classmethod
    def _preserve_secret_placeholders(cls, incoming, existing, key: str | None = None):
        if key is not None and cls._is_secret_key(key) and incoming == SECRET_PLACEHOLDER:
            return existing
        if isinstance(incoming, dict):
            old = existing if isinstance(existing, dict) else {}
            return {
                item_key: cls._preserve_secret_placeholders(item, old.get(item_key), str(item_key))
                for item_key, item in incoming.items()
            }
        if isinstance(incoming, list):
            old = existing if isinstance(existing, list) else []
            return [
                cls._preserve_secret_placeholders(item, old[index] if index < len(old) else None)
                for index, item in enumerate(incoming)
            ]
        return incoming

    @staticmethod
    def _is_secret_key(key: str) -> bool:
        normalized = key.strip().lower().replace("-", "_")
        return any(marker in normalized for marker in SECRET_KEY_MARKERS)

    @staticmethod
    def _require_text(value: str, message: str) -> str:
        text = value.strip()
        if not text:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)
        return text
