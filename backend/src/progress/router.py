from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.exceptions import NotFoundError
from src.progress import service
from src.progress.schemas import UserTaskProgress, UserTaskProgressCreate, UserTaskProgressUpdate
from src.schemas import Error


router = APIRouter(prefix='/user_task_progress', tags=['Progress'])


@router.get(
    '',
    response_model=list[UserTaskProgress],
    summary='Получить прогресс пользователя',
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': Error, 'description': 'user_id обязателен'},
    },
)
async def get_user_progress(
    user_id: UUID,
    module_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[UserTaskProgress]:
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='user_id is required',
        )
    progress_list = await service.get_user_progress(db, user_id, module_id)
    return [UserTaskProgress.model_validate(p) for p in progress_list]


@router.post(
    '',
    response_model=UserTaskProgress,
    status_code=status.HTTP_201_CREATED,
    summary='Создать запись прогресса',
)
async def create_progress(
    progress_data: UserTaskProgressCreate,
    db: AsyncSession = Depends(get_db),
) -> UserTaskProgress:
    progress = await service.create_progress(db, progress_data)
    return UserTaskProgress.model_validate(progress)


@router.patch(
    '/{id}',
    response_model=UserTaskProgress,
    summary='Обновить прогресс',
    responses={
        status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Запись прогресса не найдена'},
    },
)
async def update_progress(
    id: UUID,
    progress_data: UserTaskProgressUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserTaskProgress:
    try:
        progress = await service.update_progress(db, id, progress_data)
        return UserTaskProgress.model_validate(progress)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Progress not found',
        )
