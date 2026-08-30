"""预警相关请求/响应模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class IntelligenceBaseModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FeedbackCategoryNode(IntelligenceBaseModel):
    code: str
    name: str
    parent_code: str | None = None
    level: Literal["category", "type", "subtype"]
    children: list["FeedbackCategoryNode"] = Field(default_factory=list)


WarningRuleType = Literal[
    "dayRise",
    "weekRise",
    "suspect",
    "repeat",
    "pcsDayHb30",
    "pcsWeekHb30",
    "pcsMonthHb30",
    "pcsMonthTb30",
]


class IntelligenceSuspectWarningQueryModel(IntelligenceBaseModel):
    page_num: int = 1
    page_size: int = 20
    keyword: str | None = None
    rysfz: str | None = None
    ryxm: str | None = None
    sdpcs: str | None = None
    sdpcsdm: str | None = None
    org_code: str | None = None
    org_name: str | None = None
    jjdbh: str | None = None
    tjwdbq: str | None = None
    bjlb: str | None = None
    bjlx: str | None = None
    handle_status: str | None = None
    begin_rq: str | None = None
    end_rq: str | None = None
    begin_bjsj: str | None = None
    end_bjsj: str | None = None
    view_mode: Literal["summary", "detail"] = "summary"
    dept_scope_code: str | None = None
    dept_scope_name: str | None = None


class IntelligenceSuspectWarningHandleModel(IntelligenceBaseModel):
    handle_status: Literal["0", "1", "2"]
    handle_remark: str | None = None


class IntelligenceSuspectWarningModel(IntelligenceBaseModel):
    xlbh: int | None = None
    lx: str | None = None
    rq: str | None = None
    sdpcsdm: str | None = None
    sdpcs: str | None = None
    tjwdbq: str | None = None
    tsrybq: str | None = None
    ryxm: str | None = None
    rysfz: str | None = None
    jjdbh: str | None = None
    bjsj: str | None = None
    jqsl: str | None = None
    tjsj: str | None = None
    handle_status: str | None = "0"
    handle_remark: str | None = None
    handle_by: str | None = None
    handle_time: datetime | None = None
    warning_text: str | None = None
    alarm_count: int | None = None
    rule_type: WarningRuleType | None = "suspect"
    group_key: str | None = None


class IntelligenceWeekRiseWarningQueryModel(IntelligenceBaseModel):
    page_num: int = 1
    page_size: int = 20
    keyword: str | None = None
    sdpcs: str | None = None
    sdpcsdm: str | None = None
    org_code: str | None = None
    org_name: str | None = None
    ajlb: str | None = None
    begin_rq: str | None = None
    end_rq: str | None = None
    dept_scope_code: str | None = None
    dept_scope_name: str | None = None


class IntelligenceWeekRiseWarningModel(IntelligenceBaseModel):
    xlbh: int | None = None
    week_start: str | None = None
    week_end: str | None = None
    sdpcsdm: str | None = None
    sdpcs: str | None = None
    ajlb: str | None = None
    jjzs: int | None = None
    dzjqhb: str | None = None
    sz_pcsjjzs: int | None = None
    sz_jqhb: str | None = None
    ssz_pcsjjzs: int | None = None
    ssz_jqhb: str | None = None
    tjsj: str | None = None
    warning_text: str | None = None
    rule_type: WarningRuleType | None = "weekRise"


class IntelligenceDayRiseWarningQueryModel(IntelligenceBaseModel):
    page_num: int = 1
    page_size: int = 20
    keyword: str | None = None
    sdpcs: str | None = None
    sdpcsdm: str | None = None
    org_code: str | None = None
    org_name: str | None = None
    ajlb: str | None = None
    begin_rq: str | None = None
    end_rq: str | None = None
    dept_scope_code: str | None = None
    dept_scope_name: str | None = None


class IntelligenceDayRiseWarningModel(IntelligenceBaseModel):
    xlbh: int | None = None
    rq: str | None = None
    sdpcsdm: str | None = None
    sdpcs: str | None = None
    ajlb: str | None = None
    jjzs: int | None = None
    drjqhb: str | None = None
    zr_pcsjjzs: int | None = None
    zr_jqhb: str | None = None
    qr_pcsjjzs: int | None = None
    qr_jqhb: str | None = None
    tjsj: str | None = None
    warning_text: str | None = None
    rule_type: WarningRuleType | None = "dayRise"


class IntelligencePcsMxWarningQueryModel(IntelligenceBaseModel):
    page_num: int = 1
    page_size: int = 20
    keyword: str | None = None
    sdpcs: str | None = None
    sdpcsdm: str | None = None
    org_code: str | None = None
    org_name: str | None = None
    ajlb: str | None = None
    begin_rq: str | None = None
    end_rq: str | None = None
    dept_scope_code: str | None = None
    dept_scope_name: str | None = None


class IntelligenceRepeatWarningQueryModel(IntelligenceBaseModel):
    page_num: int = 1
    page_size: int = 20
    keyword: str | None = None
    ryxm: str | None = None
    rysfz: str | None = None
    dhhm: str | None = None
    org_code: str | None = None
    org_name: str | None = None
    pcsdm: str | None = None
    pcsmc: str | None = None
    begin_bjsj: str | None = None
    end_bjsj: str | None = None
    begin_rq: str | None = None
    end_rq: str | None = None
    view_mode: Literal["summary", "detail"] = "summary"
    dept_scope_code: str | None = None
    dept_scope_name: str | None = None


class IntelligenceRepeatWarningModel(IntelligenceBaseModel):
    xlbh: int | None = None
    lx: str | None = None
    tjsj: str | None = None
    ryxm: str | None = None
    rysfz: str | None = None
    dhhm: str | None = None
    pcsdm: str | None = None
    pcsmc: str | None = None
    sdpcsdm: str | None = None
    sdpcs: str | None = None
    jjdbh: str | None = None
    bjsj: str | None = None
    bjcs: int | None = None
    warning_text: str | None = None
    rule_type: WarningRuleType | None = "repeat"
    group_key: str | None = None
