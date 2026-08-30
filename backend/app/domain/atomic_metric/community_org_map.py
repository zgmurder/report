"""社区 → 片区/共建委/警务区 组织维度映射。"""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from app.repositories.community_org_repository import CommunityOrgRepository

OrgDimension = Literal['pianqu', 'gongjianwei', 'jingwuqu']

ORG_DIMENSION_LABELS: dict[str, str] = {
    'pianqu': '片区',
    'gongjianwei': '共建委',
    'jingwuqu': '警务区',
}

_VALID = frozenset(ORG_DIMENSION_LABELS)


def normalize_org_dimension(raw: Any) -> OrgDimension | None:
    value = str(raw or '').strip().lower()
    if not value:
        return None
    aliases = {
        '片区': 'pianqu',
        'area': 'pianqu',
        'pianqu': 'pianqu',
        '共建委': 'gongjianwei',
        '工作委员会': 'gongjianwei',
        'committee': 'gongjianwei',
        'gongjianwei': 'gongjianwei',
        '警务区': 'jingwuqu',
        'zone': 'jingwuqu',
        'jingwuqu': 'jingwuqu',
    }
    mapped = aliases.get(value) or aliases.get(str(raw or '').strip())
    if mapped in _VALID:
        return mapped  # type: ignore[return-value]
    return None


def org_dimension_label(dim: str | None) -> str:
    return ORG_DIMENSION_LABELS.get(str(dim or '').strip(), '组织维度')


def load_community_org_map(db: Session) -> list[dict[str, Any]]:
    return CommunityOrgRepository(db).list_all()


def _index_map(items: list[dict[str, Any]], org_type: OrgDimension) -> tuple[dict[str, str], dict[str, str]]:
    by_code: dict[str, str] = {}
    by_name: dict[str, str] = {}
    for item in items:
        if str(item.get('org_type') or '') != org_type:
            continue
        org_name = str(item.get('org_name') or '').strip()
        if not org_name:
            continue
        code = str(item.get('fasqdm') or '').strip()
        if code:
            by_code[code] = org_name
        names = {str(item.get('fasqmc') or '').strip()}
        for alias in item.get('aliases') or []:
            names.add(str(alias or '').strip())
        for name in names:
            if name:
                by_name[name] = org_name
    return by_code, by_name


def resolve_org_name(
    *,
    fasqdm: str | None,
    fasqmc: str | None,
    org_type: OrgDimension,
    by_code: dict[str, str],
    by_name: dict[str, str],
) -> str | None:
    code = str(fasqdm or '').strip()
    name = str(fasqmc or '').strip()
    if code and code in by_code:
        return by_code[code]
    if name and name in by_name:
        return by_name[name]
    # 官方名带派出所前缀时，尝试后缀命中短名
    if name:
        for short, org_name in by_name.items():
            if len(short) >= 2 and name.endswith(short):
                return org_name
    return None


def fold_community_rows_by_org(
    db: Session,
    rows: list[dict[str, Any]],
    *,
    org_type: OrgDimension,
) -> list[dict[str, Any]]:
    """将社区统计行按组织维度折叠。

    输入兼容：
    - fasqdm/fasqmc/total
    - unit_code/unit_name/today_cnt/mom_cnt/yoy_cnt
    输出统一为社区同比结构，便于复用格式化与趋势逻辑。
    """
    items = load_community_org_map(db)
    by_code, by_name = _index_map(items, org_type)
    bucket: dict[str, dict[str, int]] = {}
    for row in rows or []:
        code = str(row.get('fasqdm') or row.get('unit_code') or '').strip()
        name = str(row.get('fasqmc') or row.get('unit_name') or '').strip()
        org_name = resolve_org_name(
            fasqdm=code,
            fasqmc=name,
            org_type=org_type,
            by_code=by_code,
            by_name=by_name,
        )
        if not org_name:
            continue
        try:
            today = int(
                float(
                    row.get('total')
                    if row.get('total') is not None
                    else (row.get('today_cnt') or 0)
                )
            )
        except (TypeError, ValueError):
            today = 0
        try:
            mom = int(float(row.get('mom_cnt') or row.get('mom_total') or 0))
        except (TypeError, ValueError):
            mom = 0
        try:
            yoy = int(float(row.get('yoy_cnt') or row.get('yoy_total') or 0))
        except (TypeError, ValueError):
            yoy = 0
        slot = bucket.setdefault(org_name, {'today': 0, 'mom': 0, 'yoy': 0})
        slot['today'] += max(today, 0)
        slot['mom'] += max(mom, 0)
        slot['yoy'] += max(yoy, 0)

    folded: list[dict[str, Any]] = []
    for org_name, nums in bucket.items():
        if nums['today'] <= 0 and nums['mom'] <= 0 and nums['yoy'] <= 0:
            continue
        folded.append(
            {
                'unit_code': org_name,
                'unit_name': org_name,
                'fasqdm': org_name,
                'fasqmc': org_name,
                'today_cnt': nums['today'],
                'mom_cnt': nums['mom'],
                'yoy_cnt': nums['yoy'],
                'total': nums['today'],
            }
        )
    folded.sort(key=lambda r: (-int(r['today_cnt']), str(r['unit_name'])))
    return folded
