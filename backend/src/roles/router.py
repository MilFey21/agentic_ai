from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.exceptions import ConflictException, NotFoundException
from src.roles import service
from src.roles.schemas import Role, RoleCreate, RoleUpdate


router = APIRouter(prefix='/roles', tags=['Roles'])


@router.get('', response_model=list[Role], summary='Получить список ролей')
async def get_roles(db: AsyncSession = Depends(get_db)) -> list[Role]:
    return await service.get_all_roles(db)


@router.get('/{role_id}', response_model=Role, summary='Получить роль по ID')
async def get_role_by_id(role_id: UUID, db: AsyncSession = Depends(get_db)) -> Role:
    role = await service.get_role_by_id(db, role_id)
    if not role:
        raise NotFoundException('Role not found')
    return role


@router.post(
    '',
    response_model=Role,
    status_code=status.HTTP_201_CREATED,
    summary='Создать роль',
    responses={status.HTTP_409_CONFLICT: {'description': 'Role with this name already exists'}},
)
async def create_role(role_data: RoleCreate, db: AsyncSession = Depends(get_db)) -> Role:
    existing_role = await service.get_role_by_name(db, role_data.name)
    if existing_role:
        raise ConflictException('Role with this name already exists')
    return await service.create_role(db, role_data)


@router.patch('/{role_id}', response_model=Role, summary='Обновить роль')
async def update_role(role_id: UUID, role_data: RoleUpdate, db: AsyncSession = Depends(get_db)) -> Role:
    role = await service.update_role(db, role_id, role_data)
    if not role:
        raise NotFoundException('Role not found')
    return role


@router.delete('/{role_id}', status_code=status.HTTP_204_NO_CONTENT, summary='Удалить роль')
async def delete_role(role_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    role = await service.delete_role(db, role_id)
    if not role:
        raise NotFoundException('Role not found')
