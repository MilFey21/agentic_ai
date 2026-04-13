from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session_maker


async def get_db() -> AsyncGenerator[AsyncSession]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session
