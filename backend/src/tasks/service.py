from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid5

from src.course.loader import course_loader
from src.course.schemas import AssignmentMeta
from src.tasks.schemas import Task


NAMESPACE_MODULE = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_TASK = UUID('6ba7b811-9dad-11d1-80b4-00c04fd430c8')


def _string_to_uuid(string_id: str, namespace: UUID) -> UUID:
    return uuid5(namespace, string_id)


def _assignment_meta_to_task_dict(assignment_meta: AssignmentMeta) -> dict:
    task_id = _string_to_uuid(assignment_meta.id, NAMESPACE_TASK)
    module_id = _string_to_uuid(assignment_meta.module_id, NAMESPACE_MODULE)
    now = datetime.now(UTC)
    return {
        'id': task_id,
        'module_id': module_id,
        'flow_id': None,
        'title': assignment_meta.title,
        'type': assignment_meta.type,
        'description': assignment_meta.description,
        'max_score': assignment_meta.max_score,
        'achievement_badge': None,
        'created_at': now,
        'updated_at': None,
        'deleted_at': None,
    }


async def get_task_by_id(db: Any, task_id: UUID) -> Task | None:
    assignments = course_loader.get_assignments()
    for assignment_meta in assignments:
        assignment_uuid = _string_to_uuid(assignment_meta.id, NAMESPACE_TASK)
        if assignment_uuid == task_id:
            task_dict = _assignment_meta_to_task_dict(assignment_meta)
            return Task.model_validate(task_dict)
    return None


async def get_all_tasks(
    db: Any,
    module_id: UUID | None = None,
    flow_id: UUID | None = None,
) -> list[Task]:
    module_id_str = None
    if module_id:
        modules = course_loader.get_modules(active_only=False)
        for module_meta in modules:
            module_uuid = _string_to_uuid(module_meta.id, NAMESPACE_MODULE)
            if module_uuid == module_id:
                module_id_str = module_meta.id
                break

    assignments_meta = course_loader.get_assignments(module_id=module_id_str)
    tasks = []
    for assignment_meta in assignments_meta:
        task_dict = _assignment_meta_to_task_dict(assignment_meta)
        tasks.append(Task.model_validate(task_dict))
    return tasks


async def create_task(db: Any, task_data: Any) -> Task:
    raise NotImplementedError('Tasks are read-only. Edit course/assignments/*.json files.')


async def update_task(db: Any, task_id: UUID, task_data: Any) -> Task:
    raise NotImplementedError('Tasks are read-only. Edit course/assignments/*.json files.')


async def delete_task(db: Any, task_id: UUID) -> None:
    raise NotImplementedError('Tasks are read-only. Edit course/assignments/*.json files.')
