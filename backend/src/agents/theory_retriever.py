"""
TheoryRetriever — детерминированный keyword-search поверх индексированных Markdown-файлов.

Архитектурное решение (см. system-design.md §1.3):
  LLM НЕ участвует в поиске контекста — только в его интерпретации и генерации ответа.
  Это снижает латентность, стоимость и непредсказуемость retrieval-контура.

Алгоритм поиска:
  - Строится лес секционных деревьев (по одному дереву на .md-файл).
  - Каждый узел: heading, level, content, full_content, terms, breadcrumb.
  - Взвешенная оценка узла:
      s(v, q) = 1.0 × |T_v ∩ T_q|  +  3.0 × I[heading(v) ⊂ q]  +  0.5 / level(v)
  - Победитель: argmax s(v, q) при s > 0;
    fallback — корневой узел файла темы задания.
  - Инкрементальная переиндексация по file mtime.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional


# ---------------------------------------------------------------------------
# Структуры данных
# ---------------------------------------------------------------------------


@dataclass
class SectionNode:
    """Узел дерева секций Markdown-файла."""

    heading: str
    level: int              # 1 = H1, 2 = H2, …
    content: str            # Текст только этой секции (без дочерних)
    full_content: str       # Текст секции + всех дочерних (заполняется после сборки дерева)
    terms: list[str]        # Ключевые термины из heading + content
    breadcrumb: str         # «filename > H1 > H2 > …»
    children: list[SectionNode] = field(default_factory=list)


@dataclass
class TheoryContent:
    """Результат поиска по теории (совместимый интерфейс с предыдущей версией)."""

    content: str
    source_file: str
    confidence: float
    related_concepts: list[str]
    breadcrumb: str = ''


# ---------------------------------------------------------------------------
# TheoryRetriever
# ---------------------------------------------------------------------------


class TheoryRetriever:
    """
    Детерминированный keyword-search по индексированным Markdown-файлам курса.

    Параметры конструктора:
        theory_dir: путь к папке с .md-файлами. По умолчанию — course/theory
                    относительно backend/.

    Публичный API:
        search(query, task_topic) → SectionNode | None
        get_theory(query, topic, depth) → TheoryContent
    """

    def __init__(self, theory_dir: Optional[str] = None) -> None:
        if theory_dir is None:
            # agents/theory_retriever.py → agents/ → src/ → backend/
            current_file = Path(__file__).resolve()
            backend_dir = current_file.parent.parent.parent
            theory_dir = backend_dir / 'course' / 'theory'

        self.theory_dir = Path(theory_dir)

        # Лес деревьев секций: {имя_файла_без_.md → список корневых узлов}
        self._trees: dict[str, list[SectionNode]] = {}
        # Последние mtime файлов для инкрементальной переиндексации
        self._file_mtimes: dict[str, float] = {}
        # Кэш результатов get_theory
        self._cache: dict[str, TheoryContent] = {}

        self._build_index()

    # ------------------------------------------------------------------
    # Индексация
    # ------------------------------------------------------------------

    def _build_index(self) -> None:
        """Построить/обновить индекс из .md-файлов (инкрементально по mtime)."""
        if not self.theory_dir.exists():
            return

        for md_file in sorted(self.theory_dir.glob('*.md')):
            mtime = md_file.stat().st_mtime
            fname = md_file.stem

            if self._file_mtimes.get(fname) == mtime:
                continue  # Файл не изменился — пропускаем

            try:
                content = md_file.read_text(encoding='utf-8')
                self._trees[fname] = self._parse_to_section_tree(content, fname)
                self._file_mtimes[fname] = mtime
                self._cache.clear()  # Инвалидировать кэш при изменении файлов
            except Exception as exc:  # noqa: BLE001
                # Битый файл не должен ломать всю систему
                print(f'[TheoryRetriever] Warning: cannot read {md_file}: {exc}')

    def _parse_to_section_tree(self, content: str, filename: str) -> list[SectionNode]:
        """Распарсить Markdown в лес секционных деревьев."""
        lines = content.split('\n')
        heading_re = re.compile(r'^(#{1,6})\s+(.+)$')

        # Найти все заголовки с позициями
        headings: list[tuple[int, int, str]] = []  # (line_idx, level, heading_text)
        for i, line in enumerate(lines):
            m = heading_re.match(line)
            if m:
                headings.append((i, len(m.group(1)), m.group(2).strip()))

        if not headings:
            # Нет заголовков — один корневой узел на весь файл
            terms = self._extract_terms(content)
            root = SectionNode(
                heading=filename,
                level=1,
                content=content,
                full_content=content,
                terms=terms,
                breadcrumb=filename,
            )
            return [root]

        # Создать плоский список узлов
        flat_nodes: list[SectionNode] = []
        for idx, (line_idx, level, heading) in enumerate(headings):
            next_line_idx = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
            raw_content = '\n'.join(lines[line_idx + 1 : next_line_idx]).strip()
            terms = self._extract_terms(heading + ' ' + raw_content)
            flat_nodes.append(
                SectionNode(
                    heading=heading,
                    level=level,
                    content=raw_content,
                    full_content=raw_content,  # будет обновлено ниже
                    terms=terms,
                    breadcrumb='',  # будет заполнено ниже
                )
            )

        # Собрать дерево и проставить breadcrumbs / full_content
        roots = self._assemble_tree(flat_nodes, filename)
        for root in roots:
            self._update_full_content(root)
        return roots

    def _assemble_tree(self, nodes: list[SectionNode], filename: str) -> list[SectionNode]:
        """Собрать плоский список узлов в дерево по уровням вложенности."""
        roots: list[SectionNode] = []
        # Стек «открытых» предков (от корня к листу)
        stack: list[SectionNode] = []

        for node in nodes:
            # Убрать из стека всё с уровнем ≥ текущего
            while stack and stack[-1].level >= node.level:
                stack.pop()

            if stack:
                parent = stack[-1]
                parent.children.append(node)
                node.breadcrumb = parent.breadcrumb + ' > ' + node.heading
            else:
                roots.append(node)
                node.breadcrumb = filename + ' > ' + node.heading

            stack.append(node)

        return roots

    def _update_full_content(self, node: SectionNode) -> str:
        """Рекурсивно обновить full_content = content + все дочерние."""
        child_parts = [self._update_full_content(c) for c in node.children]
        parts = [node.content] + child_parts
        node.full_content = '\n\n'.join(p for p in parts if p).strip()
        return node.full_content

    # ------------------------------------------------------------------
    # Утилиты термино-извлечения
    # ------------------------------------------------------------------

    _STOP_WORDS = frozenset({
        'и', 'в', 'на', 'с', 'по', 'для', 'что', 'как', 'это', 'не', 'от', 'из',
        'the', 'a', 'an', 'of', 'in', 'to', 'for', 'is', 'are', 'be', 'it',
        'that', 'this', 'with', 'or', 'and', 'but',
    })

    def _extract_terms(self, text: str) -> list[str]:
        """Извлечь ключевые термины: токены + bold + code."""
        # Обычные слова ≥ 3 символов, без стоп-слов
        words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ][a-zA-Zа-яА-ЯёЁ]{2,}\b', text)
        terms: set[str] = {w.lower() for w in words if w.lower() not in self._STOP_WORDS}

        # Термины в **bold**
        for t in re.findall(r'\*\*([^*]+)\*\*', text):
            terms.update(w.lower() for w in t.split() if w.lower() not in self._STOP_WORDS)

        # Термины в `code`
        for t in re.findall(r'`([^`]+)`', text):
            terms.update(w.lower() for w in t.split() if w.lower() not in self._STOP_WORDS)

        return list(terms)

    # ------------------------------------------------------------------
    # Поиск
    # ------------------------------------------------------------------

    def _score(self, node: SectionNode, query_terms: set[str], query_lower: str) -> float:
        """
        Оценить релевантность узла запросу.

        s(v, q) = 1.0 × |T_v ∩ T_q|  +  3.0 × I[heading(v) ⊂ q]  +  0.5 / level(v)
        """
        term_overlap = len(set(node.terms) & query_terms)
        heading_in_query = 1.0 if node.heading.lower() in query_lower else 0.0
        level_bonus = 0.5 / max(node.level, 1)
        return 1.0 * term_overlap + 3.0 * heading_in_query + level_bonus

    def _iter_all_nodes(self, roots: list[SectionNode]) -> Iterator[SectionNode]:
        """BFS-итератор по всем узлам дерева."""
        queue = list(roots)
        while queue:
            node = queue.pop(0)
            yield node
            queue.extend(node.children)

    def search(self, query: str, task_topic: Optional[str] = None) -> Optional[SectionNode]:
        """
        Найти наиболее релевантный узел по детерминированной формуле.

        Args:
            query:      Запрос пользователя (вопрос, тема).
            task_topic: Имя файла (без .md) для fallback, если s == 0.

        Returns:
            Наиболее релевантный SectionNode, или None если индекс пуст.
        """
        # Инкрементальная переиндексация
        self._build_index()

        query_lower = query.lower()
        query_terms = set(self._extract_terms(query))

        best_node: Optional[SectionNode] = None
        best_score = 0.0

        for _fname, roots in self._trees.items():
            for node in self._iter_all_nodes(roots):
                s = self._score(node, query_terms, query_lower)
                if s > best_score:
                    best_score = s
                    best_node = node

        if best_node is not None and best_score > 0:
            return best_node

        # Fallback 1: корневой узел файла темы задания
        if task_topic and task_topic in self._trees:
            roots = self._trees[task_topic]
            if roots:
                return roots[0]

        # Fallback 2: первый корневой узел из любого файла
        for roots in self._trees.values():
            if roots:
                return roots[0]

        return None

    # ------------------------------------------------------------------
    # Публичный API (совместимый с предыдущей версией)
    # ------------------------------------------------------------------

    def get_theory(
        self,
        query: str,
        topic: Optional[str] = None,
        depth: str = 'basic',
    ) -> TheoryContent:
        """
        Получить теоретический контекст по запросу.

        Args:
            query:  Запрос агента (что нужно найти).
            topic:  Конкретная тема / имя файла для фокусировки.
            depth:  Уровень детализации: basic / intermediate / advanced.

        Returns:
            TheoryContent с релевантным содержимым, источником и уверенностью.
        """
        cache_key = f'{query}:{topic}:{depth}'
        if cache_key in self._cache:
            return self._cache[cache_key]

        node = self.search(query, task_topic=topic)

        if node is None:
            result = TheoryContent(
                content='Теоретический материал не найден для данного запроса.',
                source_file='none',
                confidence=0.0,
                related_concepts=[],
            )
            self._cache[cache_key] = result
            return result

        # Ограничение контента по уровню глубины
        content = node.full_content
        limits = {'basic': 1000, 'intermediate': 2000}
        limit = limits.get(depth)
        if limit and len(content) > limit:
            content = content[:limit] + '\n…'

        # Связанные концепты — заголовки прямых потомков
        related = [child.heading for child in node.children[:5]]

        result = TheoryContent(
            content=content,
            source_file=node.breadcrumb.split(' > ')[0] if node.breadcrumb else 'unknown',
            confidence=min(1.0, len(set(node.terms) & set(self._extract_terms(query))) / max(len(set(self._extract_terms(query))), 1)),
            related_concepts=related,
            breadcrumb=node.breadcrumb,
        )
        self._cache[cache_key] = result
        return result
