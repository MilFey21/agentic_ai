from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.assistants.models import AssistantProfile
from src.assistants.schemas import AssistantProfileCreate, AssistantProfileUpdate
from src.exceptions import NotFoundError


async def get_assistant_profile_by_id(
    db: AsyncSession,
    profile_id: UUID,
) -> AssistantProfile | None:
    query = select(AssistantProfile).where(
        AssistantProfile.id == profile_id,
        AssistantProfile.deleted_at.is_(None),
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_all_assistant_profiles(
    db: AsyncSession,
    module_id: UUID | None = None,
) -> list[AssistantProfile]:
    query = select(AssistantProfile).where(AssistantProfile.deleted_at.is_(None))
    if module_id:
        query = query.where(AssistantProfile.module_id == module_id)
    query = query.order_by(AssistantProfile.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_assistant_profile(
    db: AsyncSession,
    profile_data: AssistantProfileCreate,
) -> AssistantProfile:
    profile = AssistantProfile(**profile_data.model_dump())
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def update_assistant_profile(
    db: AsyncSession,
    profile_id: UUID,
    profile_data: AssistantProfileUpdate,
) -> AssistantProfile:
    update_data = profile_data.model_dump(exclude_unset=True)
    if not update_data:
        profile = await get_assistant_profile_by_id(db, profile_id)
        if not profile:
            raise NotFoundError('AssistantProfile')
        return profile

    query = (
        update(AssistantProfile)
        .where(
            AssistantProfile.id == profile_id,
            AssistantProfile.deleted_at.is_(None),
        )
        .values(**update_data)
        .returning(AssistantProfile)
    )
    result = await db.execute(query)
    await db.commit()
    profile = result.scalar_one_or_none()
    if not profile:
        raise NotFoundError('AssistantProfile')
    return profile


async def delete_assistant_profile(db: AsyncSession, profile_id: UUID) -> None:
    from datetime import UTC, datetime

    query = (
        update(AssistantProfile)
        .where(
            AssistantProfile.id == profile_id,
            AssistantProfile.deleted_at.is_(None),
        )
        .values(deleted_at=datetime.now(UTC))
    )
    result = await db.execute(query)
    await db.commit()
    if result.rowcount == 0:
        raise NotFoundError('AssistantProfile')
