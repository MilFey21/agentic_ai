from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.exceptions import NotFoundError
from src.modules import service
from src.modules.schemas import Module
from src.schemas import Error


router = APIRouter(prefix='/modules', tags=['Modules'])


@router.get('', response_model=list[Module], summary='Получить все модули')
async def get_modules(
    db: AsyncSession = Depends(get_db),
) -> list[Module]:
    modules = await service.get_all_modules(db, active_only=True)
    return [Module.model_validate(m) for m in modules]


@router.get(
    '/{id}',
    response_model=Module,
    summary='Получить модуль по ID',
    responses={
        status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Модуль не найден'},
    },
)
async def get_module_by_id(
    id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Module:
    module = await service.get_module_by_id(db, id)
    if not module:
        raise NotFoundError('Module')
    return Module.model_validate(module)


@router.post(
    '',
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
    summary='Создать модуль (отключено)',
)
async def create_module() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail='Modules are read-only. Edit course/modules/*.json files.',
    )


@router.patch(
    '/{id}',
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
    summary='Обновить модуль (отключено)',
)
async def update_module() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail='Modules are read-only. Edit course/modules/*.json files.',
    )


@router.delete(
    '/{id}',
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
    summary='Удалить модуль (отключено)',
)
async def delete_module() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail='Modules are read-only. Edit course/modules/*.json files.',
    )
