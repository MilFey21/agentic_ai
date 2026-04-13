from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid5

from src.course.loader import course_loader
from src.course.schemas import ModuleMeta
from src.modules.schemas import Module


NAMESPACE_MODULE = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_TASK = UUID('6ba7b811-9dad-11d1-80b4-00c04fd430c8')


def _string_to_uuid(string_id: str, namespace: UUID) -> UUID:
    return uuid5(namespace, string_id)


def _module_meta_to_module_dict(module_meta: ModuleMeta) -> dict:
    module_id = _string_to_uuid(module_meta.id, NAMESPACE_MODULE)
    now = datetime.now(UTC)
    return {
        'id': module_id,
        'title': module_meta.title,
        'description': module_meta.description,
        'flow_id': None,
        'is_active': module_meta.is_active,
        'created_at': now,
        'updated_at': None,
        'deleted_at': None,
    }


async def get_module_by_id(db: Any, module_id: UUID) -> Module | None:
    modules = course_loader.get_modules(active_only=False)
    for module_meta in modules:
        module_uuid = _string_to_uuid(module_meta.id, NAMESPACE_MODULE)
        if module_uuid == module_id:
            module_dict = _module_meta_to_module_dict(module_meta)
            return Module.model_validate(module_dict)
    return None


async def get_all_modules(db: Any, active_only: bool = True) -> list[Module]:
    modules_meta = course_loader.get_modules(active_only=active_only)
    modules = []
    for module_meta in modules_meta:
        module_dict = _module_meta_to_module_dict(module_meta)
        modules.append(Module.model_validate(module_dict))
    return modules


async def create_module(db: Any, module_data: Any) -> Module:
    raise NotImplementedError('Modules are read-only. Edit course/modules/*.json files.')


async def update_module(db: Any, module_id: UUID, module_data: Any) -> Module:
    raise NotImplementedError('Modules are read-only. Edit course/modules/*.json files.')


async def delete_module(db: Any, module_id: UUID) -> None:
    raise NotImplementedError('Modules are read-only. Edit course/modules/*.json files.')
