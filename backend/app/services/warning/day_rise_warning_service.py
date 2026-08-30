"""警情主类连续三天上升预警服务。"""

from sqlalchemy.orm import Session

from app.domain.atomic_metric.exceptions import ServiceException
from app.repositories.warning.day_rise_warning_dao import DayRiseWarningDao
from app.schemas.warning import IntelligenceDayRiseWarningQueryModel
from app.utils.camel_case import CamelCaseUtil


class DayRiseWarningService:
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
        if value is None or value == '':
            return None
        try:
            return int(float(str(value).strip().replace(',', '')))
        except (TypeError, ValueError):
            return None

    @classmethod
    def is_strict_rise(cls, row: dict) -> bool:
        """三日数量严格递增且环比均 > 0（持平不计）。"""
        jjzs = cls._parse_count(row.get('jjzs'))
        zr = cls._parse_count(row.get('zrPcsjjzs') if row.get('zrPcsjjzs') is not None else row.get('zr_pcsjjzs'))
        qr = cls._parse_count(row.get('qrPcsjjzs') if row.get('qrPcsjjzs') is not None else row.get('qr_pcsjjzs'))
        q3r = cls._parse_count(
            row.get('q3rPcsjjzs') if row.get('q3rPcsjjzs') is not None else row.get('q3r_pcsjjzs')
        )
        if None in (jjzs, zr, qr, q3r):
            return False
        if not (jjzs > zr > qr > q3r):
            return False
        rates = [
            cls._parse_rate(row.get('drjqhb')),
            cls._parse_rate(row.get('zrJqhb') if row.get('zrJqhb') is not None else row.get('zr_jqhb')),
            cls._parse_rate(row.get('qrJqhb') if row.get('qrJqhb') is not None else row.get('qr_jqhb')),
        ]
        return all(rate is not None and rate > 0 for rate in rates)

    @classmethod
    def build_warning_text(cls, row: dict) -> str:
        sdpcs = str(row.get('sdpcs') or '未知单位').strip()
        ajlb = str(row.get('ajlb') or '未知').strip()
        rq = str(row.get('rq') or '-').strip()
        qr = row.get('qrPcsjjzs') if row.get('qrPcsjjzs') is not None else row.get('qr_pcsjjzs')
        zr = row.get('zrPcsjjzs') if row.get('zrPcsjjzs') is not None else row.get('zr_pcsjjzs')
        jjzs = row.get('jjzs')
        qr_hb = str(row.get('qrJqhb') or row.get('qr_jqhb') or '-').strip()
        zr_hb = str(row.get('zrJqhb') or row.get('zr_jqhb') or '-').strip()
        dr_hb = str(row.get('drjqhb') or '-').strip()
        station = sdpcs if (sdpcs.endswith('所') or sdpcs.endswith('市') or '大队' in sdpcs) else f'{sdpcs}所'
        return (
            f'{station}{ajlb}类警情数量环比截止{rq}，连续三天上升，'
            f'分别为{qr if qr is not None else "-"}起（{qr_hb}）、'
            f'{zr if zr is not None else "-"}起（{zr_hb}）、'
            f'{jjzs if jjzs is not None else "-"}起（{dr_hb}）。'
        )

    @classmethod
    def _to_int(cls, value):
        parsed = cls._parse_count(value)
        return parsed if parsed is not None else value

    @classmethod
    def _to_row(cls, item) -> dict:
        if isinstance(item, dict):
            data = dict(item)
        else:
            data = CamelCaseUtil.transform_result(item) if item is not None else {}
        if not isinstance(data, dict):
            return {}
        for key in ('xlbh', 'sdpcsdm', 'tjsj'):
            if data.get(key) is not None:
                data[key] = str(data[key]).strip() if key != 'tjsj' else str(data[key])[:19]
        for key in ('jjzs', 'zrPcsjjzs', 'qrPcsjjzs', 'q3rPcsjjzs'):
            if data.get(key) is not None:
                data[key] = cls._to_int(data[key])
        data['ruleType'] = 'dayRise'
        data['warningText'] = cls.build_warning_text(data)
        return data

    @classmethod
    def list_page(cls, db: Session, query: IntelligenceDayRiseWarningQueryModel):
        page = DayRiseWarningDao.list_page(db, query)
        rows = []
        for item in page.rows or []:
            data = cls._to_row(item)
            if cls.is_strict_rise(data):
                rows.append(data)
        page.rows = rows
        return page

    @classmethod
    def get_detail(cls, db: Session, xlbh: int) -> dict:
        row = DayRiseWarningDao.get_by_xlbh(db, xlbh)
        if not row:
            raise ServiceException(message='三天上升预警记录不存在')
        data = cls._to_row(row)
        if not cls.is_strict_rise(data):
            raise ServiceException(message='三天上升预警记录不存在')
        return data

    @classmethod
    def summary(
        cls,
        db: Session,
        dept_scope_code: str | None = None,
        dept_scope_name: str | None = None,
    ) -> dict:
        return DayRiseWarningDao.summary(db, dept_scope_code, dept_scope_name)
