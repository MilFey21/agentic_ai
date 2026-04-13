from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.exceptions import NotFoundError
from src.flows import service
from src.flows.schemas import Flow
from src.schemas import Error


router = APIRouter(prefix='/flows', tags=['Flows'])


@router.get(
    '',
    response_model=list[Flow],
    summary='Получить потоки',
)
async def get_flows(
    module_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[Flow]:
    flows = await service.get_all_flows(db, module_id)
    return [Flow.model_validate(f) for f in flows]


@router.get(
    '/{id}',
    response_model=Flow,
    summary='Получить поток по ID',
    responses={
        status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Поток не найден'},
    },
)
async def get_flow_by_id(
    id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Flow:
    flow = await service.get_flow_by_id(db, id)
    if not flow:
        raise NotFoundError('Flow')
    return Flow.model_validate(flow)
