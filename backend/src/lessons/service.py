from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.lessons.models import Lesson


async def get_lessons_by_flow_id(db: AsyncSession, flow_id: UUID) -> list[Lesson]:
    query = select(Lesson).where(Lesson.flow_id == flow_id, Lesson.deleted_at.is_(None)).order_by(Lesson.created_at)
    result = await db.execute(query)
    return list(result.scalars().all())
