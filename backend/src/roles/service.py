from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.roles.models import Role
from src.roles.schemas import RoleCreate, RoleUpdate


async def get_role_by_id(db: AsyncSession, role_id: UUID) -> Role | None:
    query = select(Role).where(Role.id == role_id, Role.deleted_at.is_(None))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    query = select(Role).where(Role.name == name, Role.deleted_at.is_(None))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_all_roles(db: AsyncSession) -> list[Role]:
    query = select(Role).where(Role.deleted_at.is_(None)).order_by(Role.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_role(db: AsyncSession, role_data: RoleCreate) -> Role:
    role = Role(**role_data.model_dump())
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


async def update_role(db: AsyncSession, role_id: UUID, role_data: RoleUpdate) -> Role | None:
    role = await get_role_by_id(db, role_id)
    if not role:
        return None
    for key, value in role_data.model_dump(exclude_unset=True).items():
        setattr(role, key, value)
    await db.commit()
    await db.refresh(role)
    return role


async def delete_role(db: AsyncSession, role_id: UUID) -> Role | None:
    role = await get_role_by_id(db, role_id)
    if not role:
        return None
    role.deleted_at = func.now()
    await db.commit()
    await db.refresh(role)
    return role
