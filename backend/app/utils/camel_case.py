"""ORM / Row 结果转小驼峰字典。"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.engine import Row
from sqlalchemy.orm import DeclarativeBase


def _snake_to_camel(snake_str: str) -> str:
    words = snake_str.split("_")
    return words[0] + "".join(word.capitalize() for word in words[1:])


def _camel_to_snake(camel_str: str) -> str:
    words = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel_str)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", words).lower()


def _is_orm_instance(obj: Any) -> bool:
    return isinstance(obj, DeclarativeBase) or (
        hasattr(obj, "__table__") and hasattr(obj, "__dict__") and not isinstance(obj, type)
    )


def _base_to_dict(obj: Any, transform_case: str = "snake_to_camel") -> dict:
    if _is_orm_instance(obj):
        base_dict = {k: v for k, v in obj.__dict__.items() if k != "_sa_instance_state"}
    elif isinstance(obj, dict):
        base_dict = dict(obj)
    else:
        return obj
    if transform_case == "snake_to_camel":
        return {_snake_to_camel(k): v for k, v in base_dict.items()}
    if transform_case == "camel_to_snake":
        return {_camel_to_snake(k): v for k, v in base_dict.items()}
    return base_dict


def _serialize(result: Any, transform_case: str = "snake_to_camel") -> Any:
    if _is_orm_instance(result) or isinstance(result, dict):
        return _base_to_dict(result, transform_case)
    if isinstance(result, list):
        return [_serialize(row, transform_case) for row in result]
    if isinstance(result, Row):
        items = list(result)
        if items and all(_is_orm_instance(row) for row in items):
            return [_base_to_dict(row, transform_case) for row in items]
        if items and any(_is_orm_instance(row) for row in items):
            return [_serialize(row, transform_case) for row in items]
        result_dict = result._asdict()
        if transform_case == "snake_to_camel":
            return {_snake_to_camel(k): v for k, v in result_dict.items()}
        if transform_case == "camel_to_snake":
            return {_camel_to_snake(k): v for k, v in result_dict.items()}
        return result_dict
    return result


class CamelCaseUtil:
    @classmethod
    def snake_to_camel(cls, snake_str: str) -> str:
        return _snake_to_camel(snake_str)

    @classmethod
    def transform_result(cls, result: Any) -> Any:
        return _serialize(result, "snake_to_camel")
