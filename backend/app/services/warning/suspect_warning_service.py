"""嫌疑人前科/精神障碍比对预警服务。"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.atomic_metric.exceptions import ServiceException
from app.core.security import CurrentUser
from app.repositories.warning.suspect_warning_dao import SuspectWarningDao
from app.schemas.warning import (
    IntelligenceSuspectWarningHandleModel,
    IntelligenceSuspectWarningQueryModel,
)
from app.utils.camel_case import CamelCaseUtil
from app.utils.page_util import PageUtil


class SuspectWarningService:
    @classmethod
    def build_summary_text(cls, sdpcs: str | None, begin: str | None, end: str | None, count: int) -> str:
        station = str(sdpcs or '未知单位').strip()
        begin_text = str(begin or '-').strip()
        end_text = str(end or begin_text).strip()
        return f'{station} {begin_text} 至 {end_text} 前科人员相关警情共 {count} 起，点击查看详情。'

    @classmethod
    def build_case_text(
        cls,
        sdpcs: str | None,
        bjsj: str | None,
        address: str | None,
        alarm_kind: str | None,
        prior_record: str | None,
    ) -> str:
        """单条命中文案：xx所 xx时间 xx地址 接报涉 xx 警情中，有xx 前科。"""
        station = str(sdpcs or '未知单位').strip() or '未知单位'
        time_text = str(bjsj or '-').strip() or '-'
        addr = str(address or '').strip() or '未知地址'
        kind = str(alarm_kind or '').strip() or '相关'
        prior = str(prior_record or '').strip() or '相关'
        if '前科' in prior:
            prior_clause = f'有{prior}'
        else:
            prior_clause = f'有{prior} 前科'
        return f'{station} {time_text} {addr} 接报涉 {kind} 警情中，{prior_clause}，点击查看详情。'

    @classmethod
    def _pick_alarm_kind(cls, row: dict) -> str:
        for key in ('bjlxmc', 'bjlbmc', 'bjxlmc'):
            value = str(row.get(key) or '').strip()
            if value:
                return value
        category = str(row.get('alarmCategory') or '').strip()
        if category:
            return category.split('/')[0].strip() or category
        return ''

    @classmethod
    def _pick_prior_record(cls, row: dict) -> str:
        tags = [
            part.strip()
            for part in str(row.get('tsrybq') or '').replace('；', ';').split(';')
            if part and part.strip()
        ]
        if tags:
            return tags[0]
        return str(row.get('tjwdbq') or '').strip()

    @classmethod
    def _apply_case_warning_text(cls, row: dict) -> dict:
        row['warningText'] = cls.build_case_text(
            row.get('sdpcs'),
            row.get('bjsj') or row.get('rq'),
            row.get('alarmAddress'),
            cls._pick_alarm_kind(row),
            cls._pick_prior_record(row),
        )
        return row

    @classmethod
    def _normalize_handle_status(cls, status) -> str:
        if status is None or status == '':
            return '0'
        return str(status)

    @classmethod
    def _format_datetime(cls, value) -> str | None:
        if value is None or value == '':
            return None
        text = str(value).replace('T', ' ')
        return text[:19] if len(text) >= 19 else text

    @classmethod
    def _to_row(cls, item) -> dict:
        if isinstance(item, dict):
            data = dict(item)
        else:
            data = CamelCaseUtil.transform_result(item) if item is not None else {}
        if not isinstance(data, dict):
            return {}
        for key in ('xlbh', 'sdpcsdm', 'jjdbh', 'tjsj'):
            if data.get(key) is not None:
                data[key] = str(data[key]).strip()
        data['handleStatus'] = cls._normalize_handle_status(data.get('handleStatus'))
        data['ruleType'] = 'suspect'
        scope = data.get('scope') or 'station'
        data['scope'] = scope
        if data.get('alarmCount') is not None:
            try:
                data['alarmCount'] = int(data['alarmCount'])
            except (TypeError, ValueError):
                data['alarmCount'] = 0
            data['warningText'] = cls.build_summary_text(
                data.get('sdpcs'),
                data.get('rq'),
                data.get('rq'),
                data['alarmCount'],
            )
            if scope == 'city':
                data['groupKey'] = f"city|{data.get('rq') or ''}"
            else:
                data['groupKey'] = f"{data.get('sdpcsdm') or ''}|{data.get('rq') or ''}"
        else:
            # 明细文案在碰撞 jjd 后由 _apply_case_warning_text 生成
            data['warningText'] = ''
        return data

    @classmethod
    def _city_code_from_sample(cls, sample) -> str:
        text = str(sample or '').strip()
        return text[:6] if len(text) >= 6 else (text or '330782')

    @classmethod
    def list_city_summaries(cls, db: Session, query: IntelligenceSuspectWarningQueryModel) -> list[dict]:
        rows = SuspectWarningDao.list_city_summaries(db, query)
        result = []
        for row in rows:
            mapping = row._mapping if hasattr(row, '_mapping') else None
            if mapping is not None:
                rq = mapping.get('rq')
                alarm_count = mapping.get('alarm_count')
                xlbh = mapping.get('xlbh')
                tjwdbq = mapping.get('tjwdbq')
                tjsj = mapping.get('tjsj')
                sample = mapping.get('sdpcsdm_sample')
            else:
                rq, alarm_count, xlbh, tjwdbq, tjsj, sample = row
            result.append(
                cls._to_row(
                    {
                        'sdpcsdm': cls._city_code_from_sample(sample),
                        'sdpcs': '全市',
                        'rq': rq,
                        'alarmCount': alarm_count,
                        'xlbh': xlbh,
                        'tjwdbq': tjwdbq,
                        'tjsj': tjsj,
                        'scope': 'city',
                    }
                )
            )
        return result

    @classmethod
    def list_page(cls, db: Session, query: IntelligenceSuspectWarningQueryModel):
        if (query.view_mode or 'summary') == 'summary':
            page = SuspectWarningDao.list_summary_page(db, query)
            page.rows = [cls._to_row({**item, 'scope': 'station'} if isinstance(item, dict) else item) for item in (page.rows or [])]
            for row in page.rows:
                row['scope'] = 'station'
                if row.get('alarmCount') is not None:
                    row['groupKey'] = f"{row.get('sdpcsdm') or ''}|{row.get('rq') or ''}"
            return page
        page = SuspectWarningDao.list_page(db, query)
        base_rows = [cls._to_row(item) for item in (page.rows or [])]
        jjdbh_list = [str(item.get('jjdbh') or '').strip() for item in base_rows if item.get('jjdbh')]
        jjd_map = SuspectWarningDao.fetch_jjd_alarms(db, jjdbh_list)
        enriched: list[dict] = []
        for item in base_rows:
            jjdbh = str(item.get('jjdbh') or '').strip()
            row = cls._merge_jjd(item, jjd_map.get(jjdbh) if jjdbh else None)
            row['scope'] = 'detail'
            row['groupKey'] = str(row.get('xlbh') or jjdbh or '')
            cls._apply_case_warning_text(row)
            enriched.append(row)
        page.rows = enriched
        return page

    @classmethod
    def _merge_jjd(cls, base: dict, jjd: dict | None) -> dict:
        row = dict(base)
        if not jjd:
            row['jjdMatched'] = False
            row['alarmTitle'] = (row.get('ryxm') or '').strip() or '未登记姓名'
            row['alarmContent'] = row.get('jqsl') or ''
            row['alarmAddress'] = ''
            row['alarmPhone'] = ''
            row['bjlbmc'] = None
            row['bjlxmc'] = None
            row['bjxlmc'] = None
            row['alarmCategory'] = ''
            return cls._apply_case_warning_text(row)

        bjrxm = str(jjd.get('bjrxm') or '').strip()
        yhxm = str(jjd.get('yhxm') or '').strip()
        ryxm = str(row.get('ryxm') or '').strip()
        row['jjdMatched'] = True
        row['alarmTitle'] = bjrxm or yhxm or ryxm or '未登记姓名'
        if bjrxm:
            row['ryxm'] = bjrxm
        elif yhxm and not ryxm:
            row['ryxm'] = yhxm
        if jjd.get('yhsfz') and not row.get('rysfz'):
            row['rysfz'] = str(jjd.get('yhsfz')).strip()
        jjd_bjsj = cls._format_datetime(jjd.get('jjd_bjsj'))
        if jjd_bjsj:
            row['bjsj'] = jjd_bjsj
        row['alarmContent'] = str(jjd.get('bjnr') or '').strip()
        row['alarmAddress'] = str(jjd.get('afdd') or jjd.get('yhdz') or '').strip()
        row['alarmPhone'] = str(jjd.get('bjdh') or jjd.get('lxdh') or '').strip()
        row['bjlbmc'] = jjd.get('bjlbmc')
        row['bjlxmc'] = jjd.get('bjlxmc')
        row['bjxlmc'] = jjd.get('bjxlmc')
        row['jjdwmc'] = jjd.get('jjdwmc')
        category_parts = [str(x).strip() for x in (row.get('bjlbmc'), row.get('bjlxmc'), row.get('bjxlmc')) if x]
        row['alarmCategory'] = ' / '.join(category_parts) if category_parts else ''
        return cls._apply_case_warning_text(row)

    @classmethod
    def _dedupe_and_enrich(cls, rows: list[dict], jjd_map: dict[str, dict]) -> list[dict]:
        """按接警单号去重，并合并 jjd_jjd 命中警情字段。"""
        result: list[dict] = []
        seen: set[str] = set()
        for item in rows:
            jjdbh = str(item.get('jjdbh') or '').strip()
            key = jjdbh or f"xlbh:{item.get('xlbh')}"
            if key in seen:
                continue
            seen.add(key)
            result.append(cls._merge_jjd(item, jjd_map.get(jjdbh) if jjdbh else None))
        return result

    @classmethod
    def list_group_details(
        cls,
        db: Session,
        sdpcsdm: str | None,
        rq: str | None,
        sdpcs: str | None = None,
        page_num: int = 1,
        page_size: int = 50,
        city_scope: bool = False,
        bjlb: str | None = None,
        bjlx: str | None = None,
        dept_scope_code: str | None = None,
        dept_scope_name: str | None = None,
    ):
        # 全市：只按日期；派出所：精确到单位
        detail_sdpcsdm = None if city_scope else sdpcsdm
        detail_sdpcs = None if city_scope else sdpcs
        raw_page = SuspectWarningDao.list_group_details(
            db,
            sdpcsdm=detail_sdpcsdm,
            rq=rq,
            sdpcs=detail_sdpcs,
            page_num=1,
            page_size=max(page_size * 5, 500),
            bjlb=bjlb,
            bjlx=bjlx,
            dept_scope_code=dept_scope_code,
            dept_scope_name=dept_scope_name,
        )
        base_rows = [cls._to_row(item) for item in (raw_page.rows or [])]
        jjdbh_list = [str(item.get('jjdbh') or '').strip() for item in base_rows if item.get('jjdbh')]
        jjd_map = SuspectWarningDao.fetch_jjd_alarms(db, jjdbh_list)
        enriched = cls._dedupe_and_enrich(base_rows, jjd_map)
        return PageUtil.get_page_obj(enriched, page_num, page_size)

    @classmethod
    def get_detail(cls, db: Session, xlbh: int) -> dict:
        row = SuspectWarningDao.get_by_xlbh(db, xlbh)
        if not row:
            raise ServiceException(message='预警记录不存在')
        data = cls._to_row(row)
        jjdbh = str(data.get('jjdbh') or '').strip()
        if jjdbh:
            jjd_map = SuspectWarningDao.fetch_jjd_alarms(db, [jjdbh])
            data = cls._merge_jjd(data, jjd_map.get(jjdbh))
        else:
            data = cls._merge_jjd(data, None)
        return data

    @classmethod
    def handle(
        cls,
        db: Session,
        xlbh: int,
        body: IntelligenceSuspectWarningHandleModel,
        current_user: CurrentUser,
    ) -> dict:
        row = SuspectWarningDao.get_by_xlbh(db, xlbh)
        if not row:
            raise ServiceException(message='预警记录不存在')
        user_name = current_user.username if current_user else 'admin'
        SuspectWarningDao.update_handle(
            db,
            xlbh=xlbh,
            handle_status=body.handle_status,
            handle_remark=body.handle_remark,
            handle_by=user_name,
            handle_time=datetime.now(),
        )
        db.commit()
        return cls.get_detail(db, xlbh)

    @classmethod
    def summary(
        cls,
        db: Session,
        dept_scope_code: str | None = None,
        dept_scope_name: str | None = None,
    ) -> dict:
        return SuspectWarningDao.summary(db, dept_scope_code, dept_scope_name)

    @classmethod
    def label_options(cls, db: Session) -> list[str]:
        return SuspectWarningDao.list_label_options(db)
