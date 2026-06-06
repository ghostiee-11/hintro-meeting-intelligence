from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    """Base model that serializes to camelCase while accepting snake_case input.

    This keeps the public API contract aligned with the assignment examples
    (traceId, actionItems, dueDate, meetingDate) while the Python code stays
    idiomatic snake_case.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class PaginationMeta(CamelModel):
    page: int
    limit: int
    total: int
    total_pages: int


class Paginated(CamelModel, Generic[T]):
    items: list[T]
    meta: PaginationMeta


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


def build_meta(page: int, limit: int, total: int) -> PaginationMeta:
    return PaginationMeta(
        page=page,
        limit=limit,
        total=total,
        total_pages=max(1, (total + limit - 1) // limit),
    )
