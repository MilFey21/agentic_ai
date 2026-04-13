import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

# §9.1 — агентские логгеры должны писать INFO (prompt_hash, ab_group, LLM-вызовы).
# Uvicorn не добавляет handler на root-логгер, поэтому добавляем StreamHandler явно.
_agents_logger = logging.getLogger('src.agents')
if not _agents_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.INFO)
    _handler.setFormatter(logging.Formatter('%(message)s'))
    _agents_logger.addHandler(_handler)
_agents_logger.setLevel(logging.INFO)
_agents_logger.propagate = False
from fastapi.middleware.cors import CORSMiddleware

from src.agents.router import router as agents_router
from src.assistants import router as assistants_router
from src.attack_sessions import router as attack_sessions_router
from src.auth import router as auth_router
from src.chat import messages_router, router as chat_router
from src.core_config import settings
from src.database import close_db, init_db
from src.flows import router as flows_router
from src.lessons import router as lessons_router
from src.missions import router as missions_router
from src.modules import router as modules_router
from src.progress import router as progress_router
from src.roles import router as roles_router
from src.schemas import HealthResponse, RootResponse
from src.tasks import router as tasks_router
from src.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await init_db()
    yield
    await close_db()


app_configs = {
    'title': settings.APP_TITLE,
    'description': settings.APP_DESCRIPTION,
    'version': settings.APP_VERSION,
    'lifespan': lifespan,
    'root_path': '/api',
}

if not settings.show_docs:
    app_configs['openapi_url'] = None

app = FastAPI(**app_configs)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=settings.CORS_HEADERS,
)


@app.get('/', response_model=RootResponse, tags=['System'])
async def root() -> RootResponse:
    return RootResponse(
        message='WindChaserSecurity API',
        version=settings.APP_VERSION,
        status='running',
    )


@app.get('/health', response_model=HealthResponse, tags=['System'])
async def health() -> HealthResponse:
    return HealthResponse(status='healthy')


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(modules_router)
app.include_router(missions_router)
app.include_router(flows_router)
app.include_router(lessons_router)
app.include_router(tasks_router)
app.include_router(progress_router)
app.include_router(chat_router)
app.include_router(messages_router)
app.include_router(assistants_router)
app.include_router(agents_router)
app.include_router(attack_sessions_router)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        app,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', '8000')),
    )
