from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.assistants import service
from src.assistants.schemas import AssistantProfile
from src.dependencies import get_db
from src.exceptions import NotFoundError
from src.schemas import Error


router = APIRouter(prefix='/assistant_profiles', tags=['Assistants'])


@router.get(
    '',
    response_model=list[AssistantProfile],
    summary='Получить профили ассистентов',
)
async def get_assistant_profiles(
    module_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[AssistantProfile]:
    profiles = await service.get_all_assistant_profiles(db, module_id)
    return [AssistantProfile.model_validate(p) for p in profiles]


# POST endpoint removed - assistants should not be created via API
# @router.post(
#     '',
#     response_model=AssistantProfile,
#     status_code=status.HTTP_201_CREATED,
#     summary='Создать профиль ассистента',
# )
# async def create_assistant_profile(
#     profile_data: AssistantProfileCreate,
#     db: AsyncSession = Depends(get_db),
# ) -> AssistantProfile:
#     profile = await service.create_assistant_profile(db, profile_data)
#     return AssistantProfile.model_validate(profile)


@router.get(
    '/{id}',
    response_model=AssistantProfile,
    summary='Получить профиль ассистента по ID',
    responses={
        status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Профиль не найден'},
    },
)
async def get_assistant_profile_by_id(
    id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AssistantProfile:
    profile = await service.get_assistant_profile_by_id(db, id)
    if not profile:
        raise NotFoundError('AssistantProfile')
    return AssistantProfile.model_validate(profile)


# PATCH and DELETE endpoints removed - assistants should not be modified via API
# @router.patch(
#     '/{id}',
#     response_model=AssistantProfile,
#     summary='Обновить профиль ассистента',
#     responses={
#         status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Профиль не найден'},
#     },
# )
# async def update_assistant_profile(
#     id: UUID,
#     profile_data: AssistantProfileUpdate,
#     db: AsyncSession = Depends(get_db),
# ) -> AssistantProfile:
#     try:
#         profile = await service.update_assistant_profile(db, id, profile_data)
#         return AssistantProfile.model_validate(profile)
#     except NotFoundError:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail='AssistantProfile not found',
#         )
#
#
# @router.delete(
#     '/{id}',
#     status_code=status.HTTP_204_NO_CONTENT,
#     summary='Удалить профиль ассистента',
#     responses={
#         status.HTTP_404_NOT_FOUND: {'model': Error, 'description': 'Профиль не найден'},
#     },
# )
# async def delete_assistant_profile(
#     id: UUID,
#     db: AsyncSession = Depends(get_db),
# ) -> None:
#     try:
#         await service.delete_assistant_profile(db, id)
#     except NotFoundError:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail='AssistantProfile not found',
#         )
