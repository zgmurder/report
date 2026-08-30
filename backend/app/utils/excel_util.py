"""Excel 导出工具。"""

from __future__ import annotations

import io

from app.domain.atomic_metric.exceptions import ServiceException


class ExcelUtil:
    @classmethod
    def __mapping_list(cls, list_data: list, mapping_dict: dict) -> list[dict]:
        return [{mapping_dict.get(key): item.get(key) for key in mapping_dict} for item in list_data]

    @classmethod
    def export_list2excel(cls, list_data: list, mapping_dict: dict) -> bytes:
        try:
            import pandas as pd
        except ImportError as exc:
            raise ServiceException(
                message="导出依赖未安装：请安装 pandas 与 openpyxl 后重试"
            ) from exc
        mapping_data = cls.__mapping_list(list_data, mapping_dict)
        df = pd.DataFrame(mapping_data)
        binary_data = io.BytesIO()
        try:
            df.to_excel(binary_data, index=False, engine="openpyxl")
        except ImportError as exc:
            raise ServiceException(
                message="导出依赖未安装：请安装 openpyxl 后重试"
            ) from exc
        return binary_data.getvalue()
