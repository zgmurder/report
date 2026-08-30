"""警情主类连续两周上升预警服务。"""

from sqlalchemy.orm import Session

from app.domain.atomic_metric.exceptions import ServiceException
from app.repositories.warning.week_rise_warning_dao import WeekRiseWarningDao
from app.schemas.warning import IntelligenceWeekRiseWarningQueryModel
from app.utils.camel_case import CamelCaseUtil


class WeekRiseWarningService:
    @classmethod
    def _parse_rate(cls, value) -> float | None:
        text = str(value or '').strip().replace('%', '').replace(',', '')
        if not text or text in {'-', '--', 'null', 'None'}:
            return None
        try:
            return float(text)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _parse_count(cls, value) -> int | None:
        text = str(value if value is not None else '').strip().replace(',', '')
        if not text or text in {'-', '--', 'null', 'None'}:
            return None
        try:
            return int(float(text))
        except (TypeError, ValueError):
            return None

    @classmethod
    def is_strict_rise(cls, row: dict) -> bool:
        """两周数量严格递增且环比均 > 0（持平不计）：本周>上周>上上周。"""
        jjzs = cls._parse_count(row.get('jjzs'))
        sz = cls._parse_count(row.get('szPcsjjzs') if row.get('szPcsjjzs') is not None else row.get('sz_pcsjjzs'))
        ssz = cls._parse_count(row.get('sszPcsjjzs') if row.get('sszPcsjjzs') is not None else row.get('ssz_pcsjjzs'))
        if None in (jjzs, sz, ssz):
            return False
        if not (jjzs > sz > ssz):
            return False
        rates = [
            cls._parse_rate(row.get('dzjqhb')),
            cls._parse_rate(row.get('szJqhb') if row.get('szJqhb') is not None else row.get('sz_jqhb')),
        ]
        return all(rate is not None and rate > 0 for rate in rates)

    @classmethod
    def build_warning_text(cls, row: dict) -> str:
        sdpcs = str(row.get('sdpcs') or '未知单位').strip()
        ajlb = str(row.get('ajlb') or '未知').strip()
        week_end = str(row.get('weekEnd') or row.get('week_end') or '-').strip()
        sz = row.get('szPcsjjzs') if row.get('szPcsjjzs') is not None else row.get('sz_pcsjjzs')
        jjzs = row.get('jjzs')
        sz_hb = str(row.get('szJqhb') or row.get('sz_jqhb') or '-').strip()
        dz_hb = str(row.get('dzjqhb') or '-').strip()
        station = sdpcs if (sdpcs.endswith('所') or sdpcs.endswith('市') or '大队' in sdpcs) else f'{sdpcs}所'
        return (
            f'{station}{ajlb}类警情数量环比截止{week_end}，连续两周上升，'
            f'分别为{sz if sz is not None else "-"}起（{sz_hb}）、'
            f'{jjzs if jjzs is not None else "-"}起（{dz_hb}）。'
        )

    @classmethod
    def _to_row(cls, item) -> dict:
        if isinstance(item, dict):
            data = dict(item)
        else:
            data = CamelCaseUtil.transform_result(item) if item is not None else {}
        if not isinstance(data, dict):
            return {}
        for key in ('xlbh', 'sdpcsdm', 'jjzs', 'szPcsjjzs', 'sszPcsjjzs', 'tjsj'):
            if data.get(key) is not None:
                if key in {'xlbh', 'sdpcsdm'}:
                    data[key] = str(data[key]).strip()
                elif key == 'tjsj':
                    data[key] = str(data[key])[:19]
                else:
                    try:
                        data[key] = int(float(data[key]))
                    except (TypeError, ValueError):
                        pass
        data['ruleType'] = 'weekRise'
        data['warningText'] = cls.build_warning_text(data)
        return data

    @classmethod
    def list_page(cls, db: Session, query: IntelligenceWeekRiseWarningQueryModel):
        page = WeekRiseWarningDao.list_page(db, query)
        rows = []
        for item in page.rows or []:
            data = cls._to_row(item)
            if cls.is_strict_rise(data):
                rows.append(data)
        page.rows = rows
        return page

    @classmethod
    def get_detail(cls, db: Session, xlbh: int) -> dict:
        row = WeekRiseWarningDao.get_by_xlbh(db, xlbh)
        if not row:
            raise ServiceException(message='两周上升预警记录不存在')
        data = cls._to_row(row)
        if not cls.is_strict_rise(data):
            raise ServiceException(message='两周上升预警记录不存在')
        return data

    @classmethod
    def summary(
        cls,
        db: Session,
        dept_scope_code: str | None = None,
        dept_scope_name: str | None = None,
    ) -> dict:
        return WeekRiseWarningDao.summary(db, dept_scope_code, dept_scope_name)
