from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError
from src.progress.models import UserTaskProgress
from src.progress.schemas import UserTaskProgressCreate, UserTaskProgressUpdate


async def get_progress_by_id(db: AsyncSession, progress_id: UUID) -> UserTaskProgress | None:
    query = select(UserTaskProgress).where(
        UserTaskProgress.id == progress_id,
        UserTaskProgress.deleted_at.is_(None),
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_progress(
    db: AsyncSession,
    user_id: UUID,
    module_id: UUID | None = None,
) -> list[UserTaskProgress]:
    query = select(UserTaskProgress).where(
        UserTaskProgress.user_id == user_id,
        UserTaskProgress.deleted_at.is_(None),
    )
    if module_id:
        from src.tasks.models import Task

        query = query.join(Task).where(Task.module_id == module_id)
    query = query.order_by(UserTaskProgress.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_progress(
    db: AsyncSession,
    progress_data: UserTaskProgressCreate,
) -> UserTaskProgress:
    progress = UserTaskProgress(**progress_data.model_dump())
    db.add(progress)
    await db.commit()
    await db.refresh(progress)
    return progress


async def update_progress(
    db: AsyncSession,
    progress_id: UUID,
    progress_data: UserTaskProgressUpdate,
) -> UserTaskProgress:
    update_data = progress_data.model_dump(exclude_unset=True)
    if not update_data:
        progress = await get_progress_by_id(db, progress_id)
        if not progress:
            raise NotFoundError('Progress')
        return progress

    query = (
        update(UserTaskProgress)
        .where(
            UserTaskProgress.id == progress_id,
            UserTaskProgress.deleted_at.is_(None),
        )
        .values(**update_data)
        .returning(UserTaskProgress)
    )
    result = await db.execute(query)
    await db.commit()
    progress = result.scalar_one_or_none()
    if not progress:
        raise NotFoundError('Progress')
    return progress
