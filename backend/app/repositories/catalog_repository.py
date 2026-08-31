from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import DataSourceConfig, ReportTemplate, StatComponent


TEMPLATE_SEEDS = [
    ("义乌市警情日报模板", "daily", "适用于每日警情总体情况、类别变化和风险提示。", {"sections": ["总体情况", "类别分析", "风险提示"]}),
    ("派出所辖区分析模板", "district", "适用于基层所队辖区警情周报/月报。", {"sections": ["辖区概况", "高发区域", "工作建议"]}),
    ("专项研判报告模板", "special", "适用于重点类别、重点区域和重点人群专项研判。", {"sections": ["研判背景", "数据分析", "处置建议"]}),
]

COMPONENT_SEEDS = [
    ("警情总量", "text", "本地警情库", "总体情况", {"metric": "total"}),
    ("类别排行", "table", "本地警情库", "类别分析", {"group_by": "event_type"}),
    ("日趋势", "chart", "本地警情库", "趋势分析", {"chart": "line"}),
]

DATA_SOURCE_SEEDS = [
    ("本地 report 库", "mysql", "127.0.0.1", "报告系统库，警情表在 Repository 中集中适配。", {}),
    ("内置统计服务", "api", "/api/v1", "系统内置警情查询和报告统计接口。", {}),
]


class CatalogRepository:
    def __init__(self, db: Session):
        self.db = db

    def ensure_seed_data(self) -> None:
        template_count = self.db.scalar(select(func.count()).select_from(ReportTemplate)) or 0
        if template_count == 0:
            self.db.add_all([
                ReportTemplate(name=name, category=category, description=description, content_json=content, status="enabled")
                for name, category, description, content in TEMPLATE_SEEDS
            ])
        else:
            self._repair_template_seed_mojibake(template_count)

        component_count = self.db.scalar(select(func.count()).select_from(StatComponent)) or 0
        if component_count == 0:
            self.db.add_all([
                StatComponent(name=name, component_type=component_type, data_source=data_source, usage=usage, config_json=config, status="enabled")
                for name, component_type, data_source, usage, config in COMPONENT_SEEDS
            ])
        else:
            self._repair_component_seed_mojibake(component_count)

        data_source_count = self.db.scalar(select(func.count()).select_from(DataSourceConfig)) or 0
        if data_source_count == 0:
            self.db.add_all([
                DataSourceConfig(name=name, source_type=source_type, address=address, description=description, config_json=config, status="enabled")
                for name, source_type, address, description, config in DATA_SOURCE_SEEDS
            ])
        else:
            self._repair_data_source_seed_mojibake(data_source_count)

        self.db.commit()

    def _repair_template_seed_mojibake(self, count: int) -> None:
        rows = self.db.scalars(select(ReportTemplate).order_by(ReportTemplate.id.asc()).limit(3)).all()
        if count <= 3 and rows and all("模板" not in row.name for row in rows):
            for row, seed in zip(rows, TEMPLATE_SEEDS, strict=False):
                row.name, row.category, row.description, row.content_json = seed
                row.status = "enabled"

    def _repair_component_seed_mojibake(self, count: int) -> None:
        rows = self.db.scalars(select(StatComponent).order_by(StatComponent.id.asc()).limit(3)).all()
        if count <= 3 and rows and all("警情" not in row.name and "排行" not in row.name and "趋势" not in row.name for row in rows):
            for row, seed in zip(rows, COMPONENT_SEEDS, strict=False):
                row.name, row.component_type, row.data_source, row.usage, row.config_json = seed
                row.status = "enabled"

    def _repair_data_source_seed_mojibake(self, count: int) -> None:
        rows = self.db.scalars(select(DataSourceConfig).order_by(DataSourceConfig.id.asc()).limit(2)).all()
        if count <= 2 and rows and all("本地" not in row.name and "内置" not in row.name for row in rows):
            for row, seed in zip(rows, DATA_SOURCE_SEEDS, strict=False):
                row.name, row.source_type, row.address, row.description, row.config_json = seed
                row.status = "enabled"

    def list_templates(self, user_id: int) -> list[ReportTemplate]:
        return self.db.scalars(
            select(ReportTemplate)
            .where(ReportTemplate.created_by == user_id)
            .order_by(ReportTemplate.updated_at.desc(), ReportTemplate.id.desc())
        ).all()

    def get_template(self, template_id: int, user_id: int) -> ReportTemplate | None:
        return self.db.scalar(
            select(ReportTemplate).where(
                ReportTemplate.id == template_id,
                ReportTemplate.created_by == user_id,
            )
        )

    def create_template(self, data: dict) -> ReportTemplate:
        row = ReportTemplate(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_template(self, template_id: int, user_id: int, data: dict) -> ReportTemplate | None:
        row = self.get_template(template_id, user_id)
        if not row:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_template(self, template_id: int, user_id: int) -> ReportTemplate | None:
        row = self.get_template(template_id, user_id)
        if not row:
            return None
        self.db.delete(row)
        self.db.commit()
        return row

    def list_components(self) -> list[StatComponent]:
        self.ensure_seed_data()
        return self.db.scalars(select(StatComponent).order_by(StatComponent.id.asc())).all()

    def create_component(self, data: dict) -> StatComponent:
        row = StatComponent(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_component(self, component_id: int, data: dict) -> StatComponent | None:
        return self._update(StatComponent, component_id, data)

    def delete_component(self, component_id: int) -> bool:
        return self._delete(StatComponent, component_id)

    def list_data_sources(self) -> list[DataSourceConfig]:
        self.ensure_seed_data()
        return self.db.scalars(select(DataSourceConfig).order_by(DataSourceConfig.id.asc())).all()

    def get_data_source(self, data_source_id: int) -> DataSourceConfig | None:
        return self.db.get(DataSourceConfig, data_source_id)

    def create_data_source(self, data: dict) -> DataSourceConfig:
        row = DataSourceConfig(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_data_source(self, data_source_id: int, data: dict) -> DataSourceConfig | None:
        return self._update(DataSourceConfig, data_source_id, data)

    def delete_data_source(self, data_source_id: int) -> bool:
        return self._delete(DataSourceConfig, data_source_id)

    def _update(self, model, row_id: int, data: dict):
        row = self.db.get(model, row_id)
        if not row:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return row

    def _delete(self, model, row_id: int) -> bool:
        row = self.db.get(model, row_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True
