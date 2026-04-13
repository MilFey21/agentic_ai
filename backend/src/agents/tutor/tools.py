"""
Инструменты (tools) для Агента-Тьютора.

Каждый инструмент предоставляет контекстную помощь студентам в стиле
Сократического метода (SCH). Инструменты НЕ раскрывают готовые техники
атак и НЕ дают прямых ответов (SCH Priority 1).

Роль инструментов:
  - Получить теоретический контекст через TheoryRetriever.
  - Проанализировать текущее решение студента и вернуть
    направляющие вопросы, а не инструкции.
  - Вся реальная генерация ответа происходит в TutorAgent.
"""

from __future__ import annotations

from typing import Any

from src.agents.theory_retriever import TheoryRetriever


# ---------------------------------------------------------------------------
# Singleton TheoryRetriever
# ---------------------------------------------------------------------------

_theory_retriever: TheoryRetriever | None = None


def get_theory_retriever() -> TheoryRetriever:
    """Получить глобальный экземпляр TheoryRetriever (ленивая инициализация)."""
    global _theory_retriever
    if _theory_retriever is None:
        _theory_retriever = TheoryRetriever()
    return _theory_retriever


# ---------------------------------------------------------------------------
# Базовый класс
# ---------------------------------------------------------------------------


class TutoringTool:
    """
    Базовый инструмент тьютора.

    Возвращает:
        help_text:       Направляющий контекст (НЕ готовое решение).
        guiding_questions: Список Сократических вопросов.
        theory_reference: Теоретический материал из базы знаний.
        analysis_notes:  Наблюдения по текущему решению студента.
    """

    # Тема для TheoryRetriever (переопределяется в подклассах)
    _theory_topic: str = ''
    _theory_query: str = ''

    def help(
        self,
        student_question: str,
        assignment_requirements: dict[str, Any],
        student_current_solution: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def _get_theory_reference(self, extra_query: str = '') -> str:
        """Получить теоретический контекст через детерминированный retriever."""
        query = ' '.join(filter(None, [self._theory_query, extra_query]))
        tc = get_theory_retriever().get_theory(
            query=query,
            topic=self._theory_topic,
            depth='basic',
        )
        if tc.confidence > 0.0:
            related = ', '.join(tc.related_concepts[:3]) if tc.related_concepts else '—'
            return (
                f'{tc.content[:600]}\n\n'
                f'Источник: {tc.source_file} | Связанные концепции: {related}'
            )
        return ''

    @staticmethod
    def _solution_length_hint(solution: str | None) -> str:
        """Эвристическая оценка этапа по длине решения."""
        if not solution or len(solution.strip()) < 20:
            return 'no_solution'
        if len(solution.strip()) < 100:
            return 'short'
        return 'developed'


# ---------------------------------------------------------------------------
# Хелпер: system_prompt_extraction
# ---------------------------------------------------------------------------


class SystemPromptExtractionHelper(TutoringTool):
    """
    Помощь в задании «извлечение системного промпта».

    SCH P1: инструмент НИКОГДА не раскрывает конкретные промпты-атаки.
    Вместо этого — концептуальные вопросы и теоретический контекст.
    """

    _theory_topic = 'system_prompt_extraction'
    _theory_query = 'prompt injection system prompt leaking'

    def help(
        self,
        student_question: str,
        assignment_requirements: dict[str, Any],
        student_current_solution: str | None = None,
    ) -> dict[str, Any]:
        stage = self._solution_length_hint(student_current_solution)
        theory = self._get_theory_reference(student_question[:100])

        guiding_questions = self._build_guiding_questions(stage, student_current_solution)
        analysis = self._analyse_solution(stage, student_current_solution)
        help_text = self._build_help_text(stage, analysis)

        return {
            'help_text': help_text,
            'guiding_questions': guiding_questions,
            'theory_reference': theory,
            'analysis_notes': analysis,
        }

    def _build_help_text(self, stage: str, analysis: str) -> str:
        if stage == 'no_solution':
            return (
                'Начни с того, чтобы понять: какова цель бота, '
                'и как его инструкции определяют это поведение? '
                + analysis
            )
        if stage == 'short':
            return (
                'У тебя уже есть начало. Подумай: '
                'в каких ситуациях бот может раскрыть информацию о своём назначении? '
                + analysis
            )
        return (
            'Твоё решение развёрнуто — посмотри, насколько точно ты попал в цель. '
            + analysis
        )

    def _analyse_solution(self, stage: str, solution: str | None) -> str:
        if stage == 'no_solution':
            return ''
        sol = (solution or '').lower()
        notes = []
        if len(sol) > 20:
            notes.append('Есть попытка сформулировать запрос.')
        # Намеренно не указываем, что именно добавить — задаём вопросы ниже
        return ' '.join(notes)

    def _build_guiding_questions(self, stage: str, solution: str | None) -> list[str]:
        """Сократические вопросы без прямых подсказок техник."""
        base = [
            'Что определяет поведение языковой модели в диалоге?',
            'Как бот узнаёт о своих ограничениях и роли?',
            'Есть ли способ задать вопрос так, чтобы бот ответил о своей роли, '
            'а не о содержательной теме?',
        ]
        if stage == 'short':
            base += [
                'Как ты думаешь, что мешает боту ответить напрямую? '
                'Что произойдёт, если сформулировать иначе?',
                'На каком этапе обработки запроса можно «поймать» исходные инструкции?',
            ]
        if stage == 'developed':
            base += [
                'Посмотри на свой промпт: что ты уже пробовал? '
                'Какая часть была наиболее результативна и почему?',
                'Что именно вернул бот? Это похоже на системный промпт или на что-то другое?',
            ]
        return base


# ---------------------------------------------------------------------------
# Хелпер: knowledge_base_secret_extraction
# ---------------------------------------------------------------------------


class KnowledgeBaseSecretExtractionHelper(TutoringTool):
    """
    Помощь в задании «извлечение секрета из базы знаний».

    SCH P1: инструмент не раскрывает конкретные промпты-атаки на RAG.
    """

    _theory_topic = 'knowledge_base_secret_extraction'
    _theory_query = 'RAG knowledge base retrieval confidential data extraction'

    def help(
        self,
        student_question: str,
        assignment_requirements: dict[str, Any],
        student_current_solution: str | None = None,
    ) -> dict[str, Any]:
        secret_types: list[str] = assignment_requirements.get(
            'secret_types', ['athlete_logs', 'training_plans', 'incident_reports']
        )
        stage = self._solution_length_hint(student_current_solution)
        theory = self._get_theory_reference(student_question[:100])

        guiding_questions = self._build_guiding_questions(stage, secret_types)
        analysis = self._analyse_solution(stage, student_current_solution, secret_types)
        help_text = self._build_help_text(stage, secret_types)

        return {
            'help_text': help_text,
            'guiding_questions': guiding_questions,
            'theory_reference': theory,
            'analysis_notes': analysis,
        }

    def _build_help_text(self, stage: str, secret_types: list[str]) -> str:
        types_str = ', '.join(secret_types[:2]) if secret_types else 'конфиденциальные данные'
        if stage == 'no_solution':
            return (
                f'Твоя цель — получить из базы знаний защищённые данные ({types_str}). '
                'Подумай: как RAG-система решает, какие документы вернуть по запросу?'
            )
        if stage == 'short':
            return (
                'У тебя есть начальный запрос. Рассмотри: '
                'что RAG ищет в базе знаний в ответ на твой запрос — '
                'и как это связано с тем, что ты хочешь получить?'
            )
        return (
            'Твой промпт уже сформирован. Посмотри, насколько точно '
            'формулировка запроса попадает в содержимое защищённых документов.'
        )

    def _analyse_solution(
        self, stage: str, solution: str | None, secret_types: list[str]
    ) -> str:
        if stage == 'no_solution' or not solution:
            return ''
        sol_lower = solution.lower()
        # Проверяем, упоминаются ли типы данных — но не подсказываем напрямую
        secret_kw_map = {
            'athlete_logs': ['athlete', 'log', 'sport', 'спортсмен'],
            'training_plans': ['training', 'plan', 'workout', 'тренировк'],
            'incident_reports': ['incident', 'report', 'accident', 'инцидент'],
        }
        mentioned = [
            st for st in secret_types
            if any(kw in sol_lower for kw in secret_kw_map.get(st, []))
        ]
        if mentioned:
            return f'Запрос затрагивает тему: {", ".join(mentioned)}.'
        return 'Запрос пока не направлен на конкретный тип защищённых данных.'

    def _build_guiding_questions(self, stage: str, secret_types: list[str]) -> list[str]:
        base = [
            'Как RAG-система выбирает, что вернуть из базы знаний?',
            'Что влияет на то, попадёт ли защищённый документ в ответ системы?',
            'Чем отличается запрос, на который система ответит конфиденциальными данными, '
            'от обычного запроса?',
        ]
        if stage in ('short', 'developed'):
            base += [
                'Посмотри на свой запрос: насколько точно он описывает содержимое документа, '
                'который ты хочешь извлечь?',
                'Если бы ты был поисковым движком RAG, какой запрос точнее всего попал бы '
                'в нужный фрагмент?',
            ]
        return base


# ---------------------------------------------------------------------------
# Хелпер: token_limit_bypass
# ---------------------------------------------------------------------------


class TokenLimitBypassHelper(TutoringTool):
    """
    Помощь в задании «обход ограничения токенов».

    SCH P1: инструмент не раскрывает готовые промпты-атаки.
    """

    _theory_topic = 'token_limit_bypass'
    _theory_query = 'token limit max_tokens generation length LLM'

    def help(
        self,
        student_question: str,
        assignment_requirements: dict[str, Any],
        student_current_solution: str | None = None,
    ) -> dict[str, Any]:
        token_limit: int = assignment_requirements.get('token_limit', 1000)
        stage = self._solution_length_hint(student_current_solution)
        theory = self._get_theory_reference(student_question[:100])

        guiding_questions = self._build_guiding_questions(stage, token_limit)
        analysis = self._analyse_solution(stage, student_current_solution)
        help_text = self._build_help_text(stage, token_limit)

        return {
            'help_text': help_text,
            'guiding_questions': guiding_questions,
            'theory_reference': theory,
            'analysis_notes': analysis,
        }

    def _build_help_text(self, stage: str, token_limit: int) -> str:
        if stage == 'no_solution':
            return (
                f'Цель — заставить модель сгенерировать более {token_limit} токенов. '
                'Подумай: что заставляет языковую модель генерировать длинный ответ?'
            )
        if stage == 'short':
            return (
                'Промпт есть. Подумай: какой тип ответа обычно самый длинный — '
                'и как попросить именно такой?'
            )
        return (
            'Промпт развёрнут. Посмотри: достаточно ли в нём стимулов к длинной генерации, '
            'или есть что усилить?'
        )

    def _analyse_solution(self, stage: str, solution: str | None) -> str:
        if stage == 'no_solution' or not solution:
            return ''
        sol_lower = solution.lower()
        # Нейтральные наблюдения без раскрытия техник
        notes = []
        if len(solution) > 300:
            notes.append('Промпт объёмный — это может стимулировать длинный ответ.')
        elif len(solution) < 80:
            notes.append('Промпт короткий.')
        # Не перечисляем техники — только факты
        if any(w in sol_lower for w in ['list', 'every', 'all', 'перечисл', 'список']):
            notes.append('Запрос нацелен на перечисление.')
        return ' '.join(notes)

    def _build_guiding_questions(self, stage: str, token_limit: int) -> list[str]:
        base = [
            'Что в природе задачи или ответа делает генерацию длинной?',
            f'Если модель ограничена {token_limit} токенами, значит ли это, '
            'что запросить нельзя больше — или можно попробовать это обойти?',
            'Какие типы задач (пересказ, перечисление, объяснение) обычно дают '
            'более объёмные ответы?',
        ]
        if stage in ('short', 'developed'):
            base += [
                'Как ты думаешь, почему текущий промпт может не достигать лимита? '
                'Что можно добавить или изменить?',
                'Есть ли способ структурировать запрос так, '
                'чтобы модель не могла остановиться после короткого ответа?',
            ]
        return base


# ---------------------------------------------------------------------------
# Фабрика
# ---------------------------------------------------------------------------

_HELPERS: dict[str, type[TutoringTool]] = {
    'system_prompt_extraction': SystemPromptExtractionHelper,
    'knowledge_base_secret_extraction': KnowledgeBaseSecretExtractionHelper,
    'token_limit_bypass': TokenLimitBypassHelper,
}


def get_helper(assignment_type: str) -> TutoringTool:
    """Получить инструмент для типа задания."""
    cls = _HELPERS.get(assignment_type)
    if cls is None:
        raise ValueError(f'Помощник для типа «{assignment_type}» не реализован')
    return cls()
