from pydantic import BaseModel, Field


class PageResult(BaseModel):
    total: int = 0
    page: int = 1
    page_size: int = 20
    items: list = Field(default_factory=list)
