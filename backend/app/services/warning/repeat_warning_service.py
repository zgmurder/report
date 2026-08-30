"""重复涉警预警服务。"""

from sqlalchemy.orm import Session

from app.domain.atomic_metric.exceptions import ServiceException
from app.repositories.warning.repeat_warning_dao import RepeatWarningDao
from app.schemas.warning import IntelligenceRepeatWarningQueryModel
from app.utils.camel_case import CamelCaseUtil


class RepeatWarningService:
    @classmethod
    def build_summary_text(cls, ryxm: str | None, rysfz: str | None, bjcs: int | None) -> str:
        name = str(ryxm or '未知人员').strip() or '未知人员'
        sfz = str(rysfz or '-').strip() or '-'
        count = bjcs if bjcs is not None else '-'
        return f'{name}（身份证{sfz}）近一年重复涉警{count}次，点击查看详情。'

    @classmethod
    def _to_int(cls, value):
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _to_row(cls, item) -> dict:
        if isinstance(item, dict):
            data = dict(item)
        else:
            data = CamelCaseUtil.transform_result(item) if item is not None else {}
        if not isinstance(data, dict):
            return {}
        # 兼容前端复用 sdpcsdm/sdpcs 字段
        if data.get('pcsdm') is not None and data.get('sdpcsdm') is None:
            data['sdpcsdm'] = data.get('pcsdm')
        if data.get('pcsmc') is not None and data.get('sdpcs') is None:
            data['sdpcs'] = data.get('pcsmc')
        for key in ('xlbh', 'pcsdm', 'sdpcsdm', 'jjdbh', 'tjsj', 'rysfz', 'dhhm'):
            if data.get(key) is not None:
                text = str(data[key]).strip()
                data[key] = text
        if data.get('bjcs') is not None:
            data['bjcs'] = cls._to_int(data['bjcs'])
        if data.get('detailCount') is not None:
            data['detailCount'] = cls._to_int(data['detailCount'])
        person_key = data.get('personKey') or data.get('person_key')
        if not person_key:
            sfz = str(data.get('rysfz') or '').strip()
            if sfz:
                person_key = f'sfz:{sfz}'
            else:
                person_key = f"nm:{str(data.get('ryxm') or '').strip()}|{str(data.get('dhhm') or '').strip()}"
        data['groupKey'] = person_key
        data['ruleType'] = 'repeat'
        data['warningText'] = cls.build_summary_text(data.get('ryxm'), data.get('rysfz'), data.get('bjcs'))
        return data

    @classmethod
    def list_page(cls, db: Session, query: IntelligenceRepeatWarningQueryModel):
        if (query.view_mode or 'summary') == 'summary':
            page = RepeatWarningDao.list_summary_page(db, query)
            page.rows = [cls._to_row(item) for item in (page.rows or [])]
            return page
        page = RepeatWarningDao.list_page(db, query)
        page.rows = [cls._to_row(item) for item in (page.rows or [])]
        return page

    @classmethod
    def list_person_details(
        cls,
        db: Session,
        rysfz: str | None,
        ryxm: str | None = None,
        dhhm: str | None = None,
        page_num: int = 1,
        page_size: int = 50,
        dept_scope_code: str | None = None,
        dept_scope_name: str | None = None,
    ):
        page = RepeatWarningDao.list_person_details(
            db,
            rysfz=rysfz,
            ryxm=ryxm,
            dhhm=dhhm,
            page_num=page_num,
            page_size=page_size,
            dept_scope_code=dept_scope_code,
            dept_scope_name=dept_scope_name,
        )
        page.rows = [cls._to_row(item) for item in (page.rows or [])]
        return page

    @classmethod
    def get_detail(cls, db: Session, xlbh: int) -> dict:
        row = RepeatWarningDao.get_by_xlbh(db, xlbh)
        if not row:
            raise ServiceException(message='重复涉警预警记录不存在')
        return cls._to_row(row)

    @classmethod
    def summary(
        cls,
        db: Session,
        dept_scope_code: str | None = None,
        dept_scope_name: str | None = None,
    ) -> dict:
        return RepeatWarningDao.summary(db, dept_scope_code, dept_scope_name)
