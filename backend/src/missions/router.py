from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.missions import service
from src.missions.schemas import Mission
from src.schemas import Error


router = APIRouter(prefix='/missions', tags=['Missions'])


@router.get(
    '',
    response_model=list[Mission],
    summary='Получить миссии по модулю',
    responses={
        status.HTTP_400_BAD_REQUEST: {'model': Error, 'description': 'module_id обязателен'},
    },
)
async def get_missions_by_module_id(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[Mission]:
    if not module_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='module_id is required',
        )
    missions = await service.get_missions_by_module_id(db, module_id)
    return [Mission.model_validate(m) for m in missions]
