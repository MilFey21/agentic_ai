from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.missions.models import Mission


async def get_missions_by_module_id(db: AsyncSession, module_id: UUID) -> list[Mission]:
    query = (
        select(Mission).where(Mission.module_id == module_id, Mission.deleted_at.is_(None)).order_by(Mission.created_at)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
