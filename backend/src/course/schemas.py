from pydantic import BaseModel


class RubricCriterion(BaseModel):
    name: str
    description: str
    max_score: float


class Rubric(BaseModel):
    passing_threshold: float
    criteria: list[RubricCriterion]


class AssignmentMeta(BaseModel):
    id: str
    type: str
    module_id: str
    title: str
    description: str
    difficulty: str
    estimated_time_minutes: int
    max_attempts: int
    max_score: float
    passing_score: float
    rubric: Rubric
    success_criteria: list[str]
    learning_objectives: list[str]
    keywords: list[str]


class ModuleMeta(BaseModel):
    id: str
    title: str
    description: str
    is_active: bool
    assignment_ids: list[str]


class CourseData(BaseModel):
    modules: list[ModuleMeta]
    assignments: dict[str, AssignmentMeta]
