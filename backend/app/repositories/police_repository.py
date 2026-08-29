from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.police import PoliceEventQuery


class PoliceRepository:
    """警情数据访问层。

    旧系统警情主表字段尚未最终确认，第一阶段集中在本仓库适配，避免 SQL 散落。
    """

    def __init__(self, db: Session):
        self.db = db

    def list_events(self, query: PoliceEventQuery) -> tuple[int, list[dict]]:
        # TODO: 确认真实警情表和字段后替换。必须保持参数绑定，不拼接用户输入。
        return 0, []

    def overview(self, query: PoliceEventQuery) -> dict:
        # TODO: 迁移旧项目 sql/intelligence 中的统计 SQL。
        return {"total": 0, "by_type": [], "by_unit": [], "trend": []}
