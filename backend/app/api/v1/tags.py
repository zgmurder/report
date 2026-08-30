from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.core.security import CurrentUser, get_current_user
from app.domain.atomic_metric.exceptions import ServiceException
from app.schemas.tag import (
    IntelligenceAlarmRestoreModel,
    IntelligenceAlarmVerifyModel,
    IntelligenceTagPackageSaveModel,
    IntelligenceTagSearchRequest,
)
from app.services.tag_service import TagService

router = APIRouter()


@router.get("/catalog")
def list_tag_catalog(sheet: str | None = Query(default=None), db: Session = Depends(get_db)):
    try:
        return ok(TagService.list_catalog(db, sheet))
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc


@router.get("/packages")
def list_tag_packages(keyword: str | None = Query(default=None), db: Session = Depends(get_db)):
    return ok(TagService.list_packages(db, keyword))


@router.post("/packages")
def save_tag_package(
    body: IntelligenceTagPackageSaveModel,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return ok(TagService.save_package(db, body, current_user), message="保存成功")
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc


@router.put("/packages/{package_id}")
def update_tag_package(
    body: IntelligenceTagPackageSaveModel,
    package_id: int = Path(),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return ok(TagService.save_package(db, body, current_user, package_id), message="更新成功")
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc


@router.delete("/packages/{package_id}")
def delete_tag_package(package_id: int = Path(), db: Session = Depends(get_db)):
    TagService.delete_package(db, package_id)
    return ok(message="删除成功")


@router.get("/search")
def search_by_tags(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    tags: str | None = Query(default=None),
    exclude_tags: str | None = Query(default=None, alias="excludeTags"),
    sort_key: str = Query(default="bjsj", alias="sortKey"),
    sort_asc: bool = Query(default=False, alias="sortAsc"),
    page_num: int = Query(default=1, alias="pageNum", ge=1),
    page_size: int = Query(default=10, alias="pageSize", ge=1, le=200),
    cjdbh: str | None = Query(default=None),
    fkdwmc: str | None = Query(default=None),
    fkrxm: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    begin_time: str | None = Query(default=None, alias="beginTime"),
    end_time: str | None = Query(default=None, alias="endTime"),
    manual_verified: bool | None = Query(default=None, alias="manualVerified"),
):
    body = TagService.build_search_request(
        include_tags=tags,
        exclude_tags=exclude_tags,
        sort_key=sort_key,
        sort_asc=sort_asc,
        page_num=page_num,
        page_size=page_size,
        cjdbh=cjdbh,
        fkdwmc=fkdwmc,
        fkrxm=fkrxm,
        keyword=keyword,
        begin_time=begin_time,
        end_time=end_time,
        manual_verified=manual_verified,
    )
    try:
        return ok(TagService.search(db, body, current_user))
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc


@router.post("/search", include_in_schema=False)
def search_by_tags_post(
    body: IntelligenceTagSearchRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return ok(TagService.search(db, body, current_user))
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc


@router.put("/alarms/verify")
def verify_alarm_tags(
    body: IntelligenceAlarmVerifyModel,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return ok(TagService.verify_alarm(db, body, current_user), message="核对保存成功")
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc


@router.put("/alarms/restore")
def restore_alarm_tags(
    body: IntelligenceAlarmRestoreModel,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ = current_user
    try:
        return ok(TagService.restore_alarm(db, str(body.id or "")), message="已恢复为AI原始结果")
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc


@router.post("/export")
def export_by_tags(
    body: IntelligenceTagSearchRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        binary = TagService.export_search(db, body, current_user)
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc
    export_type = str(getattr(body, "export_type", None) or "alarms").strip().lower()
    filename = quote("研判包涉及人员.xlsx" if export_type == "people" else "研判包命中警情.xlsx")
    return Response(
        content=binary,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{filename}"},
    )
