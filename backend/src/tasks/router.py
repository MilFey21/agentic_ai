from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.exceptions import NotFoundError
from src.schemas import Error
from src.tasks import service
from src.tasks.schemas import Task


router = APIRouter(prefix='/tasks', tags=['Tasks'])


@router.get('', response_model=list[Task], summary='Получить задания')
async def get_tasks(
    module_id: UUID | None = None,
    flow_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[Task]:
    tasks = await service.get_all_tasks(db, module_id, flow_id)
    return [Task.model_validate(t) for t in tasks]


@router.get(
    '/{id}',
    response_model=Task,
    summary='Получить задание по ID',
    responses={
        status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Задание не найдено'},
    },
)
async def get_task_by_id(
    id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Task:
    task = await service.get_task_by_id(db, id)
    if not task:
        raise NotFoundError('Task')
    return Task.model_validate(task)


@router.post(
    '',
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
    summary='Создать задание (отключено)',
)
async def create_task() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail='Tasks are read-only. Edit course/assignments/*.json files.',
    )


@router.patch(
    '/{id}',
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
    summary='Обновить задание (отключено)',
)
async def update_task() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail='Tasks are read-only. Edit course/assignments/*.json files.',
    )


@router.delete(
    '/{id}',
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
    summary='Удалить задание (отключено)',
)
async def delete_task() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail='Tasks are read-only. Edit course/assignments/*.json files.',
    )
