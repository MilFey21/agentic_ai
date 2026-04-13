from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from src.core_config import settings


POSTGRES_INDEXES_NAMING_CONVENTION = {
    'ix': '%(column_0_label)s_idx',
    'uq': '%(table_name)s_%(column_0_name)s_key',
    'ck': '%(table_name)s_%(constraint_name)s_check',
    'fk': '%(table_name)s_%(column_0_name)s_fkey',
    'pk': '%(table_name)s_pkey',
}

metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)

engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker | None = None


def get_engine() -> AsyncEngine:
    if engine is None:
        raise RuntimeError('Database engine is not initialized')
    return engine


def get_session_maker() -> async_sessionmaker:
    if async_session_maker is None:
        raise RuntimeError('Database session maker is not initialized')
    return async_session_maker


async def init_db() -> None:
    global engine, async_session_maker  # noqa: PLW0603 (global-statement) ok here because it's a singleton

    engine = create_async_engine(
        str(settings.DATABASE_URL),
        echo=settings.ENVIRONMENT == 'local',
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

    async_session_maker = async_sessionmaker(
        engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def close_db() -> None:
    if engine is not None:
        await engine.dispose()
