from typing import Generic, List, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


class PageParams:
    def __init__(self, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int


def paginate(query, params: PageParams, serializer=lambda x: x) -> dict:
    total = query.count()
    rows = query.offset(params.offset).limit(params.page_size).all()
    return {
        "items": [serializer(r) for r in rows],
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "pages": max(1, -(-total // params.page_size)),
    }
