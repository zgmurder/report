from sqlalchemy.orm import Session

from app.repositories.police_repository import PoliceRepository
from app.schemas.common import PageResult
from app.schemas.police import PoliceEventQuery, PoliceOverview


class PoliceService:
    def __init__(self, db: Session):
        self.repository = PoliceRepository(db)

    def list_events(self, query: PoliceEventQuery) -> PageResult:
        total, items = self.repository.list_events(query)
        return PageResult(total=total, page=query.page, page_size=query.page_size, items=items)

    def overview(self, query: PoliceEventQuery) -> PoliceOverview:
        return PoliceOverview(**self.repository.overview(query))
