"""研判包 / 标签相关请求模型。"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class IntelligenceBaseModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class IntelligenceSmartTagModel(IntelligenceBaseModel):
    id: str
    name: str
    category: str
    source: str
    description: str | None = None


class IntelligenceSelectedSmartTagModel(IntelligenceSmartTagModel):
    mode: Literal["include", "exclude"] = "include"


class IntelligenceTagPackageModel(IntelligenceBaseModel):
    id: str | None = None
    name: str
    created_at: str | None = None
    remark: str | None = None
    tags: list[IntelligenceSelectedSmartTagModel] = Field(default_factory=list)
    preset: bool = False


class IntelligenceTagPackageSaveModel(IntelligenceBaseModel):
    name: str
    remark: str | None = None
    tags: list[IntelligenceSelectedSmartTagModel] = Field(default_factory=list)


class IntelligenceTagSearchRequest(IntelligenceBaseModel):
    tags: list[IntelligenceSelectedSmartTagModel] = Field(default_factory=list)
    sort_key: Literal["policeStation", "incidentCount", "bjsj"] = "bjsj"
    sort_asc: bool = False
    selected_ids: list[str] | None = None
    page_num: int = 1
    page_size: int = 10
    export_type: Literal["alarms", "people"] = "alarms"
    cjdbh: str | None = None
    fkdwmc: str | None = None
    fkrxm: str | None = None
    keyword: str | None = None
    begin_time: str | None = None
    end_time: str | None = None
    manual_verified: bool | None = None


class IntelligenceAlarmVerifyPersonModel(IntelligenceBaseModel):
    """人工核对中的单个人物要素。"""

    name: str | None = ""
    id_no: str | None = ""
    phone: str | None = ""
    nationality: str | None = ""
    roles: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    identities: list[str] = Field(default_factory=list)


class IntelligenceAlarmVerifyModel(IntelligenceBaseModel):
    """警情人工核对：增删标签后保存，并标记已核对。"""

    id: str
    alarm_tags: list[str] = Field(default_factory=list)
    dispose: list[str] = Field(default_factory=list)
    times: list[str] = Field(default_factory=list)
    places: list[str] = Field(default_factory=list)
    people: list[IntelligenceAlarmVerifyPersonModel] | None = None
    relations_text: str | None = None


class IntelligenceAlarmRestoreModel(IntelligenceBaseModel):
    """恢复为 AI 原始打标结果。"""

    id: str


class IntelligenceTagSearchResult(IntelligenceBaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    page_num: int = 1
    page_size: int = 10
    sql: str | None = None
    incident_total: int = 0
    station_total: int = 0
    people_total: int = 0
