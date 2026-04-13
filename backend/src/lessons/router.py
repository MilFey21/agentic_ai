from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.lessons import service
from src.lessons.schemas import Lesson
from src.schemas import Error


router = APIRouter(prefix='/lessons', tags=['Lessons'])


@router.get(
    '',
    response_model=list[Lesson],
    summary='Получить уроки по потоку',
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': Error, 'description': 'flow_id обязателен'},
    },
)
async def get_lessons_by_flow_id(
    flow_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[Lesson]:
    if not flow_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='flow_id is required',
        )
    lessons = await service.get_lessons_by_flow_id(db, flow_id)
    return [Lesson.model_validate(l) for l in lessons]
