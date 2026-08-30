"""派出所 mx_pcs_* 阈值预警服务。"""

from sqlalchemy.orm import Session

from app.domain.atomic_metric.exceptions import ServiceException
from app.repositories.warning.mx_pcs_warning_dao import MxPcsWarningDao
from app.models.intelligence import (
    IntelPcsDayHb30Warning,
    IntelPcsMonthHb30Warning,
    IntelPcsMonthTb30Warning,
    IntelPcsWeekHb30Warning,
)
from app.schemas.warning import IntelligencePcsMxWarningQueryModel
from app.utils.camel_case import CamelCaseUtil


class MxPcsWarningServiceBase:
    rule_type: str = ''
    entity = None
    date_column = None
    order_columns: list = []
    not_found_message = '预警记录不存在'

    @classmethod
    def _station_label(cls, sdpcs: str) -> str:
        station = str(sdpcs or '未知单位').strip()
        if station.endswith('所') or station.endswith('市') or '大队' in station:
            return station
        return f'{station}所'

    @classmethod
    def _to_int(cls, value):
        if value is None or value == '':
            return value
        try:
            return int(float(str(value).strip().replace(',', '')))
        except (TypeError, ValueError):
            return value

    @classmethod
    def build_warning_text(cls, row: dict) -> str:
        raise NotImplementedError

    @classmethod
    def _to_row(cls, item) -> dict:
        if isinstance(item, dict):
            data = dict(item)
        else:
            data = CamelCaseUtil.transform_result(item) if item is not None else {}
        if not isinstance(data, dict):
            return {}
        for key in ('xlbh', 'sdpcsdm'):
            if data.get(key) is not None:
                data[key] = str(data[key]).strip()
        if data.get('tjsj') is not None:
            data['tjsj'] = str(data['tjsj'])[:19]
        for key in ('jjzs', 'zrPcsjjzs', 'szPcsjjzs', 'syPcsjjzs', 'syJjzs'):
            if data.get(key) is not None:
                data[key] = cls._to_int(data[key])
        data['ruleType'] = cls.rule_type
        data['warningText'] = cls.build_warning_text(data)
        return data

    @classmethod
    def list_page(cls, db: Session, query: IntelligencePcsMxWarningQueryModel):
        page = MxPcsWarningDao.list_page(
            db,
            cls.entity,
            query,
            date_column=cls.date_column,
            order_columns=cls.order_columns,
        )
        page.rows = [cls._to_row(item) for item in page.rows or []]
        return page

    @classmethod
    def get_detail(cls, db: Session, xlbh: int) -> dict:
        row = MxPcsWarningDao.get_by_xlbh(db, cls.entity, xlbh)
        if not row:
            raise ServiceException(message=cls.not_found_message)
        return cls._to_row(row)

    @classmethod
    def summary(
        cls,
        db: Session,
        dept_scope_code: str | None = None,
        dept_scope_name: str | None = None,
    ) -> dict:
        return MxPcsWarningDao.summary(
            db,
            cls.entity,
            dept_scope_code=dept_scope_code,
            dept_scope_name=dept_scope_name,
        )


class PcsDayHb30WarningService(MxPcsWarningServiceBase):
    rule_type = 'pcsDayHb30'
    entity = IntelPcsDayHb30Warning
    date_column = IntelPcsDayHb30Warning.rq
    order_columns = [IntelPcsDayHb30Warning.rq, IntelPcsDayHb30Warning.jjzs]
    not_found_message = '派出所按天环比上升30%预警记录不存在'

    @classmethod
    def build_warning_text(cls, row: dict) -> str:
        station = cls._station_label(str(row.get('sdpcs') or ''))
        ajlb = str(row.get('ajlb') or '未知').strip()
        rq = str(row.get('rq') or '-').strip()
        jjzs = row.get('jjzs')
        zr = row.get('zrPcsjjzs') if row.get('zrPcsjjzs') is not None else row.get('zr_pcsjjzs')
        dr_hb = str(row.get('drjqhb') or '-').strip()
        return (
            f'{station}{ajlb}类警情数量环比截止{rq}上升{dr_hb}，'
            f'当日{jjzs if jjzs is not None else "-"}起，'
            f'昨日{zr if zr is not None else "-"}起。'
        )


class PcsWeekHb30WarningService(MxPcsWarningServiceBase):
    rule_type = 'pcsWeekHb30'
    entity = IntelPcsWeekHb30Warning
    date_column = IntelPcsWeekHb30Warning.week_end
    order_columns = [IntelPcsWeekHb30Warning.week_end, IntelPcsWeekHb30Warning.jjzs]
    not_found_message = '派出所按周环比上升30%预警记录不存在'

    @classmethod
    def build_warning_text(cls, row: dict) -> str:
        station = cls._station_label(str(row.get('sdpcs') or ''))
        ajlb = str(row.get('ajlb') or '未知').strip()
        week_end = str(row.get('weekEnd') or row.get('week_end') or '-').strip()
        jjzs = row.get('jjzs')
        sz = row.get('szPcsjjzs') if row.get('szPcsjjzs') is not None else row.get('sz_pcsjjzs')
        dz_hb = str(row.get('dzjqhb') or '-').strip()
        return (
            f'{station}{ajlb}类警情数量环比截止{week_end}上升{dz_hb}，'
            f'本周{jjzs if jjzs is not None else "-"}起，'
            f'上周{sz if sz is not None else "-"}起。'
        )


class PcsMonthHb30WarningService(MxPcsWarningServiceBase):
    rule_type = 'pcsMonthHb30'
    entity = IntelPcsMonthHb30Warning
    date_column = IntelPcsMonthHb30Warning.month_end
    order_columns = [IntelPcsMonthHb30Warning.month_end, IntelPcsMonthHb30Warning.jjzs]
    not_found_message = '派出所按月环比上升30%预警记录不存在'

    @classmethod
    def build_warning_text(cls, row: dict) -> str:
        station = cls._station_label(str(row.get('sdpcs') or ''))
        ajlb = str(row.get('ajlb') or '未知').strip()
        month_start = str(row.get('monthStart') or row.get('month_start') or '-').strip()
        month_end = str(row.get('monthEnd') or row.get('month_end') or '-').strip()
        jjzs = row.get('jjzs')
        sy = row.get('syPcsjjzs') if row.get('syPcsjjzs') is not None else row.get('sy_pcsjjzs')
        dy_hb = str(row.get('dyjqhb') or '-').strip()
        return (
            f'{station}{ajlb}类警情数量环比{month_start}至{month_end}上升{dy_hb}，'
            f'本月{jjzs if jjzs is not None else "-"}起，'
            f'上月{sy if sy is not None else "-"}起。'
        )


class PcsMonthTb30WarningService(MxPcsWarningServiceBase):
    rule_type = 'pcsMonthTb30'
    entity = IntelPcsMonthTb30Warning
    date_column = IntelPcsMonthTb30Warning.month_end
    order_columns = [IntelPcsMonthTb30Warning.month_end, IntelPcsMonthTb30Warning.jjzs]
    not_found_message = '派出所按月同比上升30%预警记录不存在'

    @classmethod
    def build_warning_text(cls, row: dict) -> str:
        station = cls._station_label(str(row.get('sdpcs') or ''))
        ajlb = str(row.get('ajlb') or '未知').strip()
        month_start = str(row.get('monthStart') or row.get('month_start') or '-').strip()
        month_end = str(row.get('monthEnd') or row.get('month_end') or '-').strip()
        jjzs = row.get('jjzs')
        sy = row.get('syJjzs') if row.get('syJjzs') is not None else row.get('sy_jjzs')
        dy_tb = str(row.get('dyjqtb') or '-').strip()
        return (
            f'{station}{ajlb}类警情数量同比{month_start}至{month_end}上升{dy_tb}，'
            f'本月{jjzs if jjzs is not None else "-"}起，'
            f'去年同期{sy if sy is not None else "-"}起。'
        )


MX_PCS_WARNING_SERVICES = {
    'pcsDayHb30': PcsDayHb30WarningService,
    'pcsWeekHb30': PcsWeekHb30WarningService,
    'pcsMonthHb30': PcsMonthHb30WarningService,
    'pcsMonthTb30': PcsMonthTb30WarningService,
}
