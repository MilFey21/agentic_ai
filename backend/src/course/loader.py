import json
from pathlib import Path

from src.course.schemas import AssignmentMeta, CourseData, ModuleMeta


class CourseLoader:
    _instance: 'CourseLoader | None' = None
    _data: CourseData | None = None

    def __new__(cls) -> 'CourseLoader':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._data is None:
            self._load_course_data()

    def _get_course_dir(self) -> Path:
        current_file = Path(__file__).resolve()
        backend_dir = current_file.parent.parent.parent
        return backend_dir / 'course'

    def _load_course_data(self) -> None:
        course_dir = self._get_course_dir()
        modules_dir = course_dir / 'modules'
        assignments_dir = course_dir / 'assignments'

        modules: list[ModuleMeta] = []
        assignments: dict[str, AssignmentMeta] = {}

        for module_file in modules_dir.glob('*.json'):
            with open(module_file, encoding='utf-8') as f:
                module_data = json.load(f)
                modules.append(ModuleMeta.model_validate(module_data))

        for assignment_file in assignments_dir.glob('*.json'):
            with open(assignment_file, encoding='utf-8') as f:
                assignment_data = json.load(f)

            assignment_id = assignment_data['id']
            md_file = assignments_dir / f'{assignment_id}.md'

            description = ''
            if md_file.exists():
                with open(md_file, encoding='utf-8') as md:
                    description = md.read()

            assignment_with_description = {
                **assignment_data,
                'description': description,
            }
            assignments[assignment_id] = AssignmentMeta.model_validate(assignment_with_description)

        self._data = CourseData(modules=modules, assignments=assignments)

    def get_modules(self, active_only: bool = True) -> list[ModuleMeta]:
        if self._data is None:
            self._load_course_data()

        modules = self._data.modules
        if active_only:
            modules = [m for m in modules if m.is_active]
        modules.sort(key=lambda x: x.title)
        return modules

    def get_module_by_id(self, module_id: str) -> ModuleMeta | None:
        modules = self.get_modules(active_only=False)
        for module in modules:
            if module.id == module_id:
                return module
        return None

    def get_assignments(
        self,
        module_id: str | None = None,
        assignment_type: str | None = None,
    ) -> list[AssignmentMeta]:
        if self._data is None:
            self._load_course_data()

        assignments_list = list(self._data.assignments.values())

        if module_id:
            assignments_list = [a for a in assignments_list if a.module_id == module_id]

        if assignment_type:
            assignments_list = [a for a in assignments_list if a.type == assignment_type]

        return assignments_list

    def get_assignment_by_id(self, assignment_id: str) -> AssignmentMeta | None:
        if self._data is None:
            self._load_course_data()

        return self._data.assignments.get(assignment_id)

    def get_assignment_by_type(self, assignment_type: str) -> AssignmentMeta | None:
        assignments = self.get_assignments(assignment_type=assignment_type)
        return assignments[0] if assignments else None

    def reload(self) -> None:
        self._data = None
        self._load_course_data()


course_loader = CourseLoader()
