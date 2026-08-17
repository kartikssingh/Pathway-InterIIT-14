"""Shared pagination.

Every list endpoint took ``skip``/``limit`` with a different hard-coded ceiling
(100, 1000, or none at all) and returned a bare array, so the frontend had no
way to know whether more rows existed. One dependency, one envelope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Sequence, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Query as SAQuery

from app.core.config import get_settings

__all__ = ["PageParams", "page_params", "Page", "paginate"]

T = TypeVar("T")


@dataclass(frozen=True)
class PageParams:
    offset: int
    limit: int

    @property
    def page_number(self) -> int:
        return (self.offset // self.limit) + 1 if self.limit else 1


def page_params(
    offset: int = Query(0, ge=0, description="Rows to skip."),
    limit: int | None = Query(None, ge=1, description="Rows to return."),
    skip: int | None = Query(None, ge=0, deprecated=True, description="Alias for offset."),
) -> PageParams:
    """Pagination dependency.

    ``skip`` is kept as a deprecated alias so existing frontend calls keep working
    while they migrate to ``offset``.
    """
    settings = get_settings()
    resolved_limit = min(limit or settings.default_page_size, settings.max_page_size)
    resolved_offset = offset or skip or 0
    return PageParams(offset=resolved_offset, limit=resolved_limit)


PageDep = Depends(page_params)


class Page(BaseModel, Generic[T]):
    """Envelope returned by every list endpoint."""

    items: list[T] = Field(default_factory=list)
    total: int = Field(0, description="Total rows matching the filter, ignoring pagination.")
    offset: int = 0
    limit: int = 0
    has_more: bool = False

    @classmethod
    def build(cls, items: Sequence[Any], total: int, params: PageParams) -> "Page[T]":
        return cls(
            items=list(items),
            total=total,
            offset=params.offset,
            limit=params.limit,
            has_more=params.offset + len(items) < total,
        )


def paginate(query: SAQuery, params: PageParams) -> tuple[list[Any], int]:
    """Apply pagination to a SQLAlchemy query and return ``(rows, total)``.

    The count runs against the same filters but without ordering or eager loads,
    which is what makes it cheap enough to do on every list request.
    """
    total = query.order_by(None).count()
    rows = query.offset(params.offset).limit(params.limit).all()
    return rows, total
