# Spec: TheoryRetriever

**Модуль**: `backend/src/agents/theory_retriever.py`  
**Версия**: 1.0  
**Статус**: PoC / Готов к реализации

---

## Назначение

TheoryRetriever обеспечивает детерминированный поиск теоретических материалов по учебным Markdown-файлам и предоставляет контекстный блок `<theory_context>` для системного промпта тьютора. LLM не участвует в поиске — только в генерации ответа по найденному контексту.

---

## Источники данных

| Источник | Путь | Формат | Объём |
|---|---|---|---|
| Теория по извлечению системного промпта | `backend/course/theory/system_prompt_extraction.md` | Markdown | ~1 файл |
| Основы prompt injection | `backend/course/theory/prompt_injection_basics.md` | Markdown | ~1 файл |
| Дополнительные материалы курса | `backend/course/theory/*.md` | Markdown | ≈14 файлов, ~120k символов |

---

## Индексация

### Структура индекса

```
ForestIndex: list[FileTree]
  FileTree:
    file_path: str
    root_node: SectionNode

SectionNode:
  heading: str
  level: int              # уровень заголовка (1–4)
  content: str            # текст секции (до следующего заголовка)
  full_content: str       # текст секции + все дочерние секции
  terms: set[str]         # нормализованные ключевые слова
  breadcrumb: str         # "H1 > H2 > H3"
  children: list[SectionNode]
```

### Инкрементальная переиндексация

- При запуске: сравнение `file.mtime` с кэшированным значением
- Переиндексация изменённых файлов: < 100 мс
- Сериализация индекса: JSON на диск (`theory_index.json`)
- Полная переиндексация по запросу: `POST /theory/reindex`

---

## Поиск

### Алгоритм скоринга

```
s(v, q) = 1.0 × |T_v ∩ T_q|  +  3.0 × I[heading(v) ⊂ q]  +  0.5 / level(v)
```

- `T_v` — множество нормализованных терминов узла v
- `T_q` — множество нормализованных токенов запроса q
- `I[heading(v) ⊂ q]` — бинарный флаг точного вхождения заголовка в запрос (β = 3.0)
- `0.5 / level(v)` — бонус за высокоуровневые секции

**Победитель**: `argmax s(v, q)` при `s > 0`.  
**Fallback**: корневой узел файла, соответствующего теме задания (`task_id → topic_file`).

### Нормализация запроса

```python
def normalize(text: str) -> set[str]:
    tokens = re.findall(r'\b\w+\b', text.lower())
    return set(t for t in tokens if len(t) > 2)
```

Стоп-слова и токены короче 3 символов отбрасываются.

---

## Reranking (опциональный)

В текущей реализации PoC используется только keyword search. LLM reranking запланирован как улучшение:

| Режим | Когда активен | Описание |
|---|---|---|
| `keyword` (default) | Всегда | Детерминированный, < 50 мс |
| `llm_rerank` (planned) | При score < порога | Дополнительный вызов LLM для ранжирования топ-5 кандидатов |

---

## Контракт API

```python
class TheoryRetriever:
    def search(self, query: str, task_id: str) -> TheoryResult:
        ...

class TheoryResult:
    node: SectionNode
    score: float
    breadcrumb: str
    is_fallback: bool       # True если использован fallback
```

**Вставка в промпт**:

```xml
<theory_context>
  <breadcrumb>{result.breadcrumb}</breadcrumb>
  <content>{result.node.full_content[:2000]}</content>
</theory_context>
```

Блок вставляется в системный промпт тьютора при каждом LLM-вызове.

---

## Производительность и ограничения

| Параметр | Значение |
|---|---|
| Целевая латентность (p95) | < 50 мс |
| Максимальный размер `full_content` в промпте | 2000 символов (~500 токенов) |
| Максимальный объём индексируемых файлов | 50 файлов, 500k символов |
| Поддерживаемые форматы | Markdown (.md) |
| Кэширование | По `(query, task_id)` → TTL 5 минут (Redis, planned) |

---

## Ошибки и fallback

| Ситуация | Поведение |
|---|---|
| `score == 0` для всего индекса | Возврат корневого узла файла темы задания |
| Файл темы задания не найден | Пустой `<theory_context>` + предупреждение в лог |
| Индекс не инициализирован | `IndexNotReadyError` → тьютор работает без контекста |
| Ошибка парсинга Markdown | Файл пропускается, предупреждение в лог, остальные файлы индексируются |

---

## Наблюдаемость

- **Лог**: каждый вызов `search()` → `{query, task_id, result_score, is_fallback, latency_ms}`
- **Метрика**: `retriever_latency_ms` (histogram, p50/p95/p99)
- **Метрика**: `retriever_fallback_total` (counter) — доля fallback-запросов
- **Алерт**: `retriever_fallback_rate > 20%` за 1 час → предупреждение
