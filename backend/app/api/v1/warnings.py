from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.core.security import CurrentUser, get_current_user
from app.domain.atomic_metric.exceptions import ServiceException
from app.domain.warning.dept_data_scope import (
    inject_query_dept_scope,
    resolve_dept_data_scope,
    row_in_dept_scope,
)
from app.schemas.warning import (
    IntelligenceDayRiseWarningQueryModel,
    IntelligencePcsMxWarningQueryModel,
    IntelligenceRepeatWarningQueryModel,
    IntelligenceSuspectWarningHandleModel,
    IntelligenceSuspectWarningQueryModel,
    IntelligenceWeekRiseWarningQueryModel,
)
from app.services.warning.day_rise_warning_service import DayRiseWarningService
from app.services.warning.incident_category_service import IncidentCategoryService
from app.services.warning.mx_pcs_warning_service import MX_PCS_WARNING_SERVICES
from app.services.warning.repeat_warning_service import RepeatWarningService
from app.services.warning.suspect_warning_service import SuspectWarningService
from app.services.warning.week_rise_warning_service import WeekRiseWarningService

router = APIRouter()

WarningRuleLiteral = Literal[
    "dayRise",
    "weekRise",
    "suspect",
    "repeat",
    "pcsDayHb30",
    "pcsWeekHb30",
    "pcsMonthHb30",
    "pcsMonthTb30",
]

RULE_META = [
    {"ruleType": "dayRise", "label": "连续三天上升", "description": "各派出所及全市警情主类连续三天环比上升", "sourceTable": "jq-total-day", "supportsHandle": False},
    {"ruleType": "weekRise", "label": "连续两周上升", "description": "各派出所及全市警情主类连续两周环比上升", "sourceTable": "jq-total-week", "supportsHandle": False},
    {"ruleType": "suspect", "label": "涉警前科", "description": "涉警人员前科比对命中预警", "sourceTable": "jq-total-qk", "supportsHandle": True},
    {"ruleType": "repeat", "label": "重复涉警", "description": "近一年重复涉警人员预警", "sourceTable": "jq-total-cf", "supportsHandle": False},
    {"ruleType": "pcsDayHb30", "label": "派出所按天环比上升30%", "description": "各派出所警情主类按天环比上升超过30%", "sourceTable": "mx_pcs_day_hb_30", "supportsHandle": False},
    {"ruleType": "pcsWeekHb30", "label": "派出所按周环比上升30%", "description": "各派出所警情主类按周环比上升超过30%", "sourceTable": "mx_pcs_week_hb_30", "supportsHandle": False},
    {"ruleType": "pcsMonthHb30", "label": "派出所按月环比上升30%", "description": "各派出所警情主类按月环比上升超过30%", "sourceTable": "mx_pcs_month_hb_30", "supportsHandle": False},
    {"ruleType": "pcsMonthTb30", "label": "派出所按月同比上升30%", "description": "各派出所警情主类按月同比上升超过30%", "sourceTable": "mx_pcs_month_tb_30", "supportsHandle": False},
]


def _mx_pcs_service(rule_type: str):
    service = MX_PCS_WARNING_SERVICES.get(rule_type)
    if service is None:
        raise ServiceException(message="未知预警规则")
    return service


def _page_payload(page: Any, extra: dict | None = None) -> dict:
    if hasattr(page, "model_dump"):
        data = page.model_dump(by_alias=True)
    elif isinstance(page, dict):
        data = dict(page)
    else:
        data = {
            "rows": getattr(page, "rows", []) or [],
            "total": getattr(page, "total", 0) or 0,
            "pageNum": getattr(page, "page_num", getattr(page, "pageNum", 1)),
            "pageSize": getattr(page, "page_size", getattr(page, "pageSize", 20)),
        }
    if extra:
        data.update(extra)
    return data


@router.get("/rules")
def warning_rules():
    return ok(RULE_META)


@router.get("/summary")
def warning_summary(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    rule_type: WarningRuleLiteral = Query(default="suspect", alias="ruleType"),
):
    scope = resolve_dept_data_scope(current_user, db)
    scope_code = None if scope.unrestricted else (scope.dept_code or None)
    scope_name = None if scope.unrestricted else (scope.dept_name or None)
    if rule_type == "dayRise":
        data = DayRiseWarningService.summary(db, scope_code, scope_name)
    elif rule_type == "weekRise":
        data = WeekRiseWarningService.summary(db, scope_code, scope_name)
    elif rule_type == "repeat":
        data = RepeatWarningService.summary(db, scope_code, scope_name)
    elif rule_type in MX_PCS_WARNING_SERVICES:
        data = _mx_pcs_service(rule_type).summary(db, scope_code, scope_name)
    else:
        data = SuspectWarningService.summary(db, scope_code, scope_name)
    data["ruleType"] = rule_type
    return ok(data)


@router.get("/labels")
def warning_labels(db: Session = Depends(get_db)):
    return ok(SuspectWarningService.label_options(db))


@router.get("/incident-categories")
def warning_incident_categories(db: Session = Depends(get_db)):
    try:
        result = IncidentCategoryService.tree(db)
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc
    return ok([item.model_dump(by_alias=True) for item in result])


@router.get("/list")
def list_warnings(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    rule_type: WarningRuleLiteral = Query(default="suspect", alias="ruleType"),
    page_num: int = Query(default=1, alias="pageNum"),
    page_size: int = Query(default=20, alias="pageSize"),
    keyword: str | None = Query(default=None),
    rysfz: str | None = Query(default=None),
    ryxm: str | None = Query(default=None),
    dhhm: str | None = Query(default=None),
    sdpcs: str | None = Query(default=None),
    sdpcsdm: str | None = Query(default=None),
    org_code: str | None = Query(default=None, alias="orgCode"),
    org_name: str | None = Query(default=None, alias="orgName"),
    pcsdm: str | None = Query(default=None),
    pcsmc: str | None = Query(default=None),
    jjdbh: str | None = Query(default=None),
    tjwdbq: str | None = Query(default=None),
    bjlb: str | None = Query(default=None),
    bjlx: str | None = Query(default=None),
    ajlb: str | None = Query(default=None),
    handle_status: str | None = Query(default=None, alias="handleStatus"),
    begin_rq: str | None = Query(default=None, alias="beginRq"),
    end_rq: str | None = Query(default=None, alias="endRq"),
    begin_bjsj: str | None = Query(default=None, alias="beginBjsj"),
    end_bjsj: str | None = Query(default=None, alias="endBjsj"),
    view_mode: Literal["summary", "detail"] = Query(default="summary", alias="viewMode"),
):
    scope = resolve_dept_data_scope(current_user, db)
    try:
        if rule_type == "dayRise":
            query = IntelligenceDayRiseWarningQueryModel(
                page_num=page_num, page_size=page_size, keyword=keyword, sdpcs=sdpcs, sdpcsdm=sdpcsdm,
                org_code=org_code, org_name=org_name, ajlb=ajlb, begin_rq=begin_rq, end_rq=end_rq,
            )
            inject_query_dept_scope(query, scope)
            return ok(_page_payload(DayRiseWarningService.list_page(db, query)))
        if rule_type == "weekRise":
            query = IntelligenceWeekRiseWarningQueryModel(
                page_num=page_num, page_size=page_size, keyword=keyword, sdpcs=sdpcs, sdpcsdm=sdpcsdm,
                org_code=org_code, org_name=org_name, ajlb=ajlb, begin_rq=begin_rq, end_rq=end_rq,
            )
            inject_query_dept_scope(query, scope)
            return ok(_page_payload(WeekRiseWarningService.list_page(db, query)))
        if rule_type == "repeat":
            query = IntelligenceRepeatWarningQueryModel(
                page_num=page_num, page_size=page_size, keyword=keyword, ryxm=ryxm, rysfz=rysfz, dhhm=dhhm,
                org_code=org_code, org_name=org_name, pcsdm=pcsdm or sdpcsdm, pcsmc=pcsmc or sdpcs,
                begin_bjsj=begin_bjsj, end_bjsj=end_bjsj, begin_rq=begin_rq, end_rq=end_rq, view_mode=view_mode,
            )
            inject_query_dept_scope(query, scope)
            return ok(_page_payload(RepeatWarningService.list_page(db, query)))
        if rule_type in MX_PCS_WARNING_SERVICES:
            query = IntelligencePcsMxWarningQueryModel(
                page_num=page_num, page_size=page_size, keyword=keyword, sdpcs=sdpcs, sdpcsdm=sdpcsdm,
                org_code=org_code, org_name=org_name, ajlb=ajlb, begin_rq=begin_rq, end_rq=end_rq,
            )
            inject_query_dept_scope(query, scope)
            return ok(_page_payload(_mx_pcs_service(rule_type).list_page(db, query)))

        query = IntelligenceSuspectWarningQueryModel(
            page_num=page_num, page_size=page_size, keyword=keyword, rysfz=rysfz, ryxm=ryxm,
            sdpcs=sdpcs, sdpcsdm=sdpcsdm, org_code=org_code, org_name=org_name, jjdbh=jjdbh, tjwdbq=tjwdbq,
            bjlb=bjlb, bjlx=bjlx, handle_status=handle_status, begin_rq=begin_rq, end_rq=end_rq,
            begin_bjsj=begin_bjsj, end_bjsj=end_bjsj, view_mode=view_mode,
        )
        inject_query_dept_scope(query, scope)
        page = SuspectWarningService.list_page(db, query)
        city_summaries = []
        if view_mode == "summary" and scope.unrestricted:
            city_summaries = SuspectWarningService.list_city_summaries(db, query)
        return ok(_page_payload(page, {"citySummaries": city_summaries}))
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc


@router.get("/suspect/details")
def suspect_group_details(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    sdpcsdm: str | None = Query(default=None),
    sdpcs: str | None = Query(default=None),
    rq: str | None = Query(default=None),
    city_scope: bool = Query(default=False, alias="cityScope"),
    bjlb: str | None = Query(default=None),
    bjlx: str | None = Query(default=None),
    page_num: int = Query(default=1, alias="pageNum"),
    page_size: int = Query(default=50, alias="pageSize"),
):
    scope = resolve_dept_data_scope(current_user, db)
    page = SuspectWarningService.list_group_details(
        db,
        sdpcsdm=sdpcsdm,
        rq=rq,
        sdpcs=sdpcs,
        page_num=page_num,
        page_size=page_size,
        city_scope=bool(city_scope) and scope.unrestricted,
        bjlb=bjlb,
        bjlx=bjlx,
        dept_scope_code=None if scope.unrestricted else (scope.dept_code or None),
        dept_scope_name=None if scope.unrestricted else (scope.dept_name or None),
    )
    return ok(_page_payload(page))


@router.get("/repeat/details")
def repeat_person_details(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    rysfz: str | None = Query(default=None),
    ryxm: str | None = Query(default=None),
    dhhm: str | None = Query(default=None),
    page_num: int = Query(default=1, alias="pageNum"),
    page_size: int = Query(default=50, alias="pageSize"),
):
    scope = resolve_dept_data_scope(current_user, db)
    page = RepeatWarningService.list_person_details(
        db,
        rysfz=rysfz,
        ryxm=ryxm,
        dhhm=dhhm,
        page_num=page_num,
        page_size=page_size,
        dept_scope_code=None if scope.unrestricted else (scope.dept_code or None),
        dept_scope_name=None if scope.unrestricted else (scope.dept_name or None),
    )
    return ok(_page_payload(page))


@router.get("/{xlbh}")
def warning_detail(
    xlbh: int = Path(),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    rule_type: WarningRuleLiteral = Query(default="suspect", alias="ruleType"),
):
    scope = resolve_dept_data_scope(current_user, db)
    try:
        if rule_type == "dayRise":
            data = DayRiseWarningService.get_detail(db, xlbh)
        elif rule_type == "weekRise":
            data = WeekRiseWarningService.get_detail(db, xlbh)
        elif rule_type == "repeat":
            data = RepeatWarningService.get_detail(db, xlbh)
        elif rule_type in MX_PCS_WARNING_SERVICES:
            data = _mx_pcs_service(rule_type).get_detail(db, xlbh)
        else:
            data = SuspectWarningService.get_detail(db, xlbh)
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc
    if not scope.unrestricted and data:
        code = data.get("sdpcsdm") or data.get("pcsdm")
        name = data.get("sdpcs") or data.get("pcsmc")
        if not row_in_dept_scope(scope=scope, dept_code=code, dept_name=name):
            raise HTTPException(status_code=403, detail="无权查看该预警记录")
    return ok(data)


@router.put("/{xlbh}/handle")
def handle_warning(
    body: IntelligenceSuspectWarningHandleModel,
    xlbh: int = Path(),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scope = resolve_dept_data_scope(current_user, db)
    try:
        if not scope.unrestricted:
            detail = SuspectWarningService.get_detail(db, xlbh)
            if not row_in_dept_scope(scope=scope, dept_code=detail.get("sdpcsdm"), dept_name=detail.get("sdpcs")):
                raise ServiceException(message="无权处理该预警记录")
        data = SuspectWarningService.handle(db, xlbh, body, current_user)
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc
    return ok(data, message="处理成功")
