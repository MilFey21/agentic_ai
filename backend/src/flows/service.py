from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.flows.models import Flow


async def get_flow_by_id(db: AsyncSession, flow_id: UUID) -> Flow | None:
    query = select(Flow).where(Flow.id == flow_id, Flow.deleted_at.is_(None))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_all_flows(db: AsyncSession, module_id: UUID | None = None) -> list[Flow]:
    query = select(Flow).where(Flow.deleted_at.is_(None))
    if module_id:
        query = query.where(Flow.module_branch_id == module_id)
    query = query.order_by(Flow.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())
