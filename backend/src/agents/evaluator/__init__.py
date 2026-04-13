"""
Агент-проверяющий для RAG Security Simulator.

Модуль содержит:
- Эвристики определения достижения цели по логам (heuristics)
- Систему рубрик для оценивания заданий
- Инструменты валидации для модуля "Атаки"
- Агента с автономным выбором инструментов
"""

from src.agents.evaluator.evaluator_agent import EvaluatorAgent
from src.agents.evaluator.heuristics import (
    get_goal_achieved,
    goal_achieved_knowledge_base_secret_extraction,
    goal_achieved_system_prompt_extraction,
    goal_achieved_token_limit_bypass,
)
from src.agents.evaluator.rubrics import (
    AssignmentType,
    Criterion,
    Rubric,
    RubricSystem,
    rubric_system,
)
from src.agents.evaluator.tools import (
    KnowledgeBaseSecretExtractionValidator,
    SystemPromptExtractionValidator,
    TokenLimitBypassValidator,
    ValidationTool,
    get_validator,
)


__all__ = [
    'AssignmentType',
    'Criterion',
    'EvaluatorAgent',
    'get_goal_achieved',
    'goal_achieved_knowledge_base_secret_extraction',
    'goal_achieved_system_prompt_extraction',
    'goal_achieved_token_limit_bypass',
    'KnowledgeBaseSecretExtractionValidator',
    'Rubric',
    'RubricSystem',
    'SystemPromptExtractionValidator',
    'TokenLimitBypassValidator',
    'ValidationTool',
    'get_validator',
    'rubric_system',
]
