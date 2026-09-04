from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.core.security import CurrentUser, get_current_user
from app.domain.atomic_metric.exceptions import ServiceException
from app.schemas.tag_v2 import IntelligenceTagV2VerifyModel
from app.services.tag_v2_service import TagV2Service

router = APIRouter()


@router.get("/catalog")
def list_tag_v2_catalog(domain: str | None = Query(default=None), db: Session = Depends(get_db)):
    try:
        return ok(TagV2Service.list_catalog(db, domain))
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc


@router.get("/security-catalog")
def list_security_tag_catalog(
    keyword: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    try:
        return ok(TagV2Service.list_security_catalog(db, keyword=keyword, limit=limit))
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc


@router.get("/stats")
def stats_tag_v2_alarms(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    level: str = Query(default="1"),
    tags: str | None = Query(default=None),
    exclude_tags: str | None = Query(default=None, alias="excludeTags"),
    domain: str | None = Query(default=None),
    fkdbh: str | None = Query(default=None),
    cjdbh: str | None = Query(default=None),
    fkdwmc: str | None = Query(default=None),
    fkdwdm: str | None = Query(default=None),
    fkrxm: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    begin_time: str | None = Query(default=None, alias="beginTime"),
    end_time: str | None = Query(default=None, alias="endTime"),
    has_manual: bool | None = Query(default=None, alias="hasManual"),
    ajlb_codes: str | None = Query(default=None, alias="ajlb"),
    ajlx_codes: str | None = Query(default=None, alias="ajlx"),
    ajxl_codes: str | None = Query(default=None, alias="ajxl"),
    limit: int = Query(default=500, ge=1, le=2000),
):
    try:
        return ok(
            TagV2Service.stats(
                db,
                current_user=current_user,
                level=level,
                include_tags=TagV2Service.parse_csv(tags),
                exclude_tags=TagV2Service.parse_csv(exclude_tags),
                domain=domain,
                fkdbh=fkdbh,
                cjdbh=cjdbh,
                fkdwmc=fkdwmc,
                fkdwdm=fkdwdm,
                fkrxm=fkrxm,
                keyword=keyword,
                begin_time=begin_time,
                end_time=end_time,
                has_manual=has_manual,
                ajlb_codes=TagV2Service.parse_csv(ajlb_codes),
                ajlx_codes=TagV2Service.parse_csv(ajlx_codes),
                ajxl_codes=TagV2Service.parse_csv(ajxl_codes),
                limit=limit,
            )
        )
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc


@router.get("/search")
def search_tag_v2_alarms(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    tags: str | None = Query(default=None),
    exclude_tags: str | None = Query(default=None, alias="excludeTags"),
    domain: str | None = Query(default=None),
    fkdbh: str | None = Query(default=None),
    cjdbh: str | None = Query(default=None),
    fkdwmc: str | None = Query(default=None),
    fkdwdm: str | None = Query(default=None),
    fkrxm: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    begin_time: str | None = Query(default=None, alias="beginTime"),
    end_time: str | None = Query(default=None, alias="endTime"),
    has_manual: bool | None = Query(default=None, alias="hasManual"),
    ajlb_codes: str | None = Query(default=None, alias="ajlb"),
    ajlx_codes: str | None = Query(default=None, alias="ajlx"),
    ajxl_codes: str | None = Query(default=None, alias="ajxl"),
    page_num: int = Query(default=1, alias="pageNum", ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=200),
):
    try:
        return ok(
            TagV2Service.search(
                db,
                current_user=current_user,
                include_tags=TagV2Service.parse_csv(tags),
                exclude_tags=TagV2Service.parse_csv(exclude_tags),
                domain=domain,
                fkdbh=fkdbh,
                cjdbh=cjdbh,
                fkdwmc=fkdwmc,
                fkdwdm=fkdwdm,
                fkrxm=fkrxm,
                keyword=keyword,
                begin_time=begin_time,
                end_time=end_time,
                has_manual=has_manual,
                ajlb_codes=TagV2Service.parse_csv(ajlb_codes),
                ajlx_codes=TagV2Service.parse_csv(ajlx_codes),
                ajxl_codes=TagV2Service.parse_csv(ajxl_codes),
                page_num=page_num,
                page_size=page_size,
            )
        )
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc


@router.get("/alarms/{fkdbh}")
def get_tag_v2_alarm_detail(
    fkdbh: str = Path(),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return ok(TagV2Service.get_alarm_detail(db, fkdbh, current_user))
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc


@router.put("/alarms/verify")
def verify_tag_v2_alarm(
    body: IntelligenceTagV2VerifyModel,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return ok(TagV2Service.verify_alarm(db, body, current_user), message="核对保存成功")
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc
