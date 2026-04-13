export const TASK_STATUS = {
  NOT_STARTED: 'not_started',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;

export type TaskStatus = (typeof TASK_STATUS)[keyof typeof TASK_STATUS];

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  [TASK_STATUS.NOT_STARTED]: 'Не начато',
  [TASK_STATUS.IN_PROGRESS]: 'В процессе',
  [TASK_STATUS.COMPLETED]: 'Завершено',
  [TASK_STATUS.FAILED]: 'Не пройдено',
};

export const TASK_TYPE = {
  THEORY: 'theory',
  PRACTICE: 'practice',
  QUIZ: 'quiz',
  ATTACK: 'attack',
  // Specific attack types
  SYSTEM_PROMPT_EXTRACTION: 'system_prompt_extraction',
  KNOWLEDGE_BASE_SECRET_EXTRACTION: 'knowledge_base_secret_extraction',
  TOKEN_LIMIT_BYPASS: 'token_limit_bypass',
} as const;

export type TaskType = (typeof TASK_TYPE)[keyof typeof TASK_TYPE];

// Attack task types that should use the attack renderer and flow
export const ATTACK_TASK_TYPES = [
  TASK_TYPE.ATTACK,
  TASK_TYPE.SYSTEM_PROMPT_EXTRACTION,
  TASK_TYPE.KNOWLEDGE_BASE_SECRET_EXTRACTION,
  TASK_TYPE.TOKEN_LIMIT_BYPASS,
] as const;

export const TASK_TYPE_LABELS: Record<string, string> = {
  [TASK_TYPE.THEORY]: 'Теория',
  [TASK_TYPE.PRACTICE]: 'Практика',
  [TASK_TYPE.QUIZ]: 'Тест',
  [TASK_TYPE.ATTACK]: 'Атака',
  [TASK_TYPE.SYSTEM_PROMPT_EXTRACTION]: 'Извлечение системного промпта',
  [TASK_TYPE.KNOWLEDGE_BASE_SECRET_EXTRACTION]: 'Извлечение секрета из БЗ',
  [TASK_TYPE.TOKEN_LIMIT_BYPASS]: 'Обход лимита токенов',
};

export const LESSON_TYPE = {
  THEORY: 'theory',
  PRACTICE: 'practice',
  QUIZ: 'quiz',
  VIDEO: 'video',
} as const;

export type LessonType = (typeof LESSON_TYPE)[keyof typeof LESSON_TYPE];

export const LESSON_TYPE_LABELS: Record<string, string> = {
  [LESSON_TYPE.THEORY]: 'Теория',
  [LESSON_TYPE.PRACTICE]: 'Практика',
  [LESSON_TYPE.QUIZ]: 'Тест',
  [LESSON_TYPE.VIDEO]: 'Видео',
};

export const SENDER_TYPE = {
  USER: 'user',
  ASSISTANT: 'assistant',
  SYSTEM: 'system',
} as const;

export type SenderType = (typeof SENDER_TYPE)[keyof typeof SENDER_TYPE];

export const ROLE = {
  ADMIN: 'admin',
  STUDENT: 'student',
  AUTHOR: 'author',
} as const;

export type RoleName = (typeof ROLE)[keyof typeof ROLE];

export const ROLE_LABELS: Record<RoleName, string> = {
  [ROLE.ADMIN]: 'Администратор',
  [ROLE.STUDENT]: 'Студент',
  [ROLE.AUTHOR]: 'Автор',
};

export const LOCAL_STORAGE_KEYS = {
  CURRENT_USER: 'windchaser_current_user',
  AUTH_TOKEN: 'windchaser_auth_token',
} as const;

