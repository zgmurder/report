"""业务数据部门范围：市局/超管看全部，其余仅本部门。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import String, cast, false, func, or_, text
from sqlalchemy.orm import Session

from app.core.security import CurrentUser


@dataclass(frozen=True)
class DeptDataScope:
    """当前账号可见部门范围。"""

    unrestricted: bool
    dept_code: str = ""
    dept_name: str = ""
    dept_id: int | None = None

    @property
    def short_dept_name(self) -> str:
        name = (self.dept_name or "").strip()
        if not name:
            return ""
        return name.replace("派出所", "").strip() or name


def is_city_dept_code(dept_code: str | None) -> bool:
    """市局部门码：有效数字去掉尾部 0 后长度 ≤ 6（如 330782000000）。"""
    digits = "".join(ch for ch in str(dept_code or "") if ch.isdigit())
    if not digits:
        return False
    stripped = digits.rstrip("0") or digits
    return len(stripped) <= 6


def is_city_bureau(dept_code: str | None = None, dept_name: str | None = None) -> bool:
    name = str(dept_name or "").strip()
    if "市局" in name:
        return True
    return is_city_dept_code(dept_code)


def _lookup_dept_name(db: Session | None, unit_code: str) -> str:
    if db is None or not unit_code:
        return ""
    try:
        row = db.execute(
            text("SELECT name FROM departments WHERE code = :code LIMIT 1"),
            {"code": unit_code},
        ).first()
        if row and row[0]:
            return str(row[0]).strip()
    except Exception:
        return ""
    return ""


def resolve_dept_data_scope(
    current_user: CurrentUser | None,
    db: Session | None = None,
) -> DeptDataScope:
    """从登录用户解析数据范围（基于 unit_code / roles，不依赖 user.dept）。"""
    if not current_user:
        return DeptDataScope(unrestricted=False)

    roles = current_user.roles or []
    username = (current_user.username or "").strip().lower()
    if "admin" in roles or username in {"admin", "administrator"}:
        unit_code = (current_user.unit_code or "").strip()
        dept_name = _lookup_dept_name(db, unit_code)
        return DeptDataScope(unrestricted=True, dept_code=unit_code, dept_name=dept_name)

    unit_code = (current_user.unit_code or "").strip()
    dept_name = _lookup_dept_name(db, unit_code)

    if is_city_bureau(unit_code, dept_name):
        return DeptDataScope(
            unrestricted=True,
            dept_code=unit_code,
            dept_name=dept_name,
        )

    return DeptDataScope(
        unrestricted=False,
        dept_code=unit_code,
        dept_name=dept_name,
    )


def dept_scope_sql(
    scope: DeptDataScope,
    *,
    code_column: str,
    name_column: str,
    param_prefix: str = "scope",
) -> tuple[str, dict]:
    """Raw-SQL equivalent of sqlalchemy_dept_match (exact/first-8/name)."""
    if scope.unrestricted:
        return "", {}
    code = (scope.dept_code or "").strip()
    name = (scope.dept_name or "").strip()
    short = scope.short_dept_name
    clauses: list[str] = []
    params: dict = {}
    if code:
        params[f"{param_prefix}_code"] = code
        clauses.append(f"TRIM(COALESCE({code_column}, '')) = :{param_prefix}_code")
        left8 = code[:8] if len(code) >= 8 else code
        if left8:
            params[f"{param_prefix}_code8"] = left8
            clauses.append(f"LEFT(TRIM(COALESCE({code_column}, '')), 8) = :{param_prefix}_code8")
    if name:
        params[f"{param_prefix}_name"] = name
        clauses.append(f"TRIM(COALESCE({name_column}, '')) = :{param_prefix}_name")
        if short and short != name:
            params[f"{param_prefix}_short"] = short
            params[f"{param_prefix}_name_like"] = f"%{short}%"
            clauses.append(f"TRIM(COALESCE({name_column}, '')) = :{param_prefix}_short")
            clauses.append(f"TRIM(COALESCE({name_column}, '')) LIKE :{param_prefix}_name_like")
    if not clauses:
        return " AND 1=0", {}
    return f" AND ({' OR '.join(clauses)})", params


def sqlalchemy_dept_match(code_column, name_column, scope: DeptDataScope):
    """SQLAlchemy 本部门匹配（代码全等 / 前8位 / 名称）。市局返回 None。"""
    if scope.unrestricted:
        return None

    parts = []
    code = (scope.dept_code or "").strip()
    name = (scope.dept_name or "").strip()
    short = scope.short_dept_name

    if code:
        code_str = cast(code_column, String)
        trimmed = func.trim(func.coalesce(code_str, ""))
        parts.append(trimmed == code)
        left8 = code[:8] if len(code) >= 8 else code
        if left8:
            parts.append(func.left(trimmed, 8) == left8)

    if name:
        name_col = func.trim(func.coalesce(name_column, ""))
        parts.append(name_col == name)
        if short and short != name:
            parts.append(name_col == short)
            parts.append(name_col.like(f"%{short}%"))

    if not parts:
        return false()
    return or_(*parts)


def apply_scope_to_org_query(query, scope: DeptDataScope):
    """非市局时强制写入本部门 org，防止前端清空/伪造越权。"""
    if scope.unrestricted or query is None:
        return query
    if scope.dept_code:
        if hasattr(query, "org_code"):
            query.org_code = scope.dept_code
        if hasattr(query, "sdpcsdm") and not (getattr(query, "org_code", None) or ""):
            query.sdpcsdm = scope.dept_code
        if hasattr(query, "pcsdm"):
            query.pcsdm = scope.dept_code
    if scope.dept_name:
        if hasattr(query, "org_name"):
            query.org_name = scope.dept_name
        if hasattr(query, "sdpcs"):
            query.sdpcs = None
        if hasattr(query, "pcsmc"):
            query.pcsmc = None
    return query


def inject_query_dept_scope(query, scope: DeptDataScope):
    """把部门范围写入查询模型（市局清空强制字段）。"""
    if query is None:
        return query
    if scope.unrestricted:
        if hasattr(query, "dept_scope_code"):
            query.dept_scope_code = None
        if hasattr(query, "dept_scope_name"):
            query.dept_scope_name = None
        return query
    if hasattr(query, "dept_scope_code"):
        query.dept_scope_code = scope.dept_code or None
    if hasattr(query, "dept_scope_name"):
        query.dept_scope_name = scope.dept_name or None
    return query


_JINHUA_LOCALITY_KEYWORDS = (
    "义乌",
    "东阳",
    "永康",
    "兰溪",
    "浦江",
    "武义",
    "磐安",
    "婺城",
    "金东",
    "金华",
)

_CITY_CODE_KEYWORD = {
    "330782": "义乌",
    "330783": "东阳",
    "330781": "兰溪",
    "330784": "永康",
    "330723": "武义",
    "330726": "浦江",
    "330727": "磐安",
    "330702": "婺城",
    "330703": "金东",
}


def resolve_city_keyword(scope: DeptDataScope | None) -> str:
    """从账号部门解析本市关键词，本项目默认义乌。"""
    if scope is None:
        return "义乌"
    name = (scope.dept_name or "").strip()
    for key in _JINHUA_LOCALITY_KEYWORDS:
        if key != "金华" and key in name:
            return key
    digits = "".join(ch for ch in str(scope.dept_code or "") if ch.isdigit())
    if len(digits) >= 6:
        return _CITY_CODE_KEYWORD.get(digits[:6], "义乌")
    return "义乌"


def restrict_fkdwmc(requested: str | None, scope: DeptDataScope) -> str | None:
    """研判/打标：非市局强制反馈单位为本部门名。"""
    if scope.unrestricted:
        req = (requested or "").strip()
        if not req:
            return None
        if is_city_bureau(None, req):
            return None
        return req
    name = (scope.dept_name or "").strip()
    if not name:
        return (requested or "").strip() or "__NO_DEPT__"
    req = (requested or "").strip()
    if not req:
        return name
    short = scope.short_dept_name
    if req == name or (short and short in req) or name in req:
        return req
    return name


def ywjq_dept_scope_sql(scope: DeptDataScope) -> tuple[str, dict]:
    """ywjq_analysis 部门/本市 SQL 片段（仅能依赖 fkdwmc）。"""
    if scope.unrestricted:
        city = resolve_city_keyword(scope)
        others = [key for key in _JINHUA_LOCALITY_KEYWORDS if key != city]
        params: dict = {}
        clauses: list[str] = []
        for index, key in enumerate(others):
            pname = f"city_ex_{index}"
            clauses.append(f"`fkdwmc` NOT LIKE :{pname} ESCAPE '\\\\'")
            params[pname] = f"%{key}%"
        if not clauses:
            return "", {}
        return f" AND ({' AND '.join(clauses)})", params

    name = (scope.dept_name or "").strip()
    short = scope.short_dept_name
    if not name and not short:
        return " AND 1=0", {}
    params = {"scope_dept_name": name or short}
    clauses = ["`fkdwmc` = :scope_dept_name"]
    if short and short != name:
        params["scope_dept_short"] = short
        params["scope_dept_like"] = f"%{short}%"
        clauses.append("`fkdwmc` = :scope_dept_short")
        clauses.append("`fkdwmc` LIKE :scope_dept_like ESCAPE '\\\\'")
    return f" AND ({' OR '.join(clauses)})", params


def row_in_dept_scope(
    *,
    scope: DeptDataScope,
    dept_code: str | None = None,
    dept_name: str | None = None,
) -> bool:
    """单行是否落在当前账号部门范围内。"""
    if scope.unrestricted:
        return True
    code = str(dept_code or "").strip()
    name = str(dept_name or "").strip()
    scope_code = (scope.dept_code or "").strip()
    scope_name = (scope.dept_name or "").strip()
    short = scope.short_dept_name

    if scope_code and code:
        if code == scope_code:
            return True
        left8 = scope_code[:8] if len(scope_code) >= 8 else scope_code
        if left8 and code[:8] == left8:
            return True
    if scope_name and name:
        if name == scope_name:
            return True
        if short and (name == short or short in name or name in scope_name):
            return True
    if scope_code or scope_name:
        return False
    return False
