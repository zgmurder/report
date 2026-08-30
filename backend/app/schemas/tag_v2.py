"""警情打标 V2 请求模型。"""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class IntelligenceBaseModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class IntelligenceTagV2VerifyModel(IntelligenceBaseModel):
    """警情打标 v2：按反馈单保存选中的标签路径。"""

    fkdbh: str
    tag_paths: list[str] = Field(default_factory=list)
