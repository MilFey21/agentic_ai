import type {
  Role,
  User,
  UserWithRole,
  Module,
  Mission,
  Flow,
  Lesson,
  Task,
  UserTaskProgress,
  AssistantProfile,
  ChatSession,
  Message,
} from '@/api/types';

// Roles
export const roles: Role[] = [
  {
    id: 'role-1',
    name: 'admin',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'role-2',
    name: 'student',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    deleted_at: null,
  },
];

// Users
export const users: User[] = [
  {
    id: 'user-1',
    role_id: 'role-1',
    username: 'admin',
    email: 'admin@windchaser.io',
    langflow_user_id: 'lf-admin-001',
    langflow_folder_id: 'lf-folder-admin',
    created_at: '2025-01-01T10:00:00Z',
    updated_at: '2025-01-01T10:00:00Z',
    deleted_at: null,
  },
  {
    id: 'user-2',
    role_id: 'role-2',
    username: 'ivan_petrov',
    email: 'ivan@example.com',
    langflow_user_id: 'lf-ivan-001',
    langflow_folder_id: 'lf-folder-ivan',
    created_at: '2025-01-15T14:30:00Z',
    updated_at: '2025-01-15T14:30:00Z',
    deleted_at: null,
  },
  {
    id: 'user-3',
    role_id: 'role-2',
    username: 'maria_sidorova',
    email: 'maria@example.com',
    langflow_user_id: 'lf-maria-001',
    langflow_folder_id: 'lf-folder-maria',
    created_at: '2025-02-01T09:00:00Z',
    updated_at: '2025-02-01T09:00:00Z',
    deleted_at: null,
  },
];

export const usersWithRoles: UserWithRole[] = users.map((user) => ({
  ...user,
  role: roles.find((r) => r.id === user.role_id)!,
}));

// Modules
export const modules: Module[] = [
  {
    id: 'mod-1',
    title: 'Основы информационной безопасности',
    description:
      'Введение в ключевые концепции информационной безопасности: угрозы, уязвимости, риски и базовые методы защиты.',
    flow_id: 'flow-1',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-03-15T12:00:00Z',
    deleted_at: null,
  },
  {
    id: 'mod-2',
    title: 'Социальная инженерия и фишинг',
    description:
      'Методы атак социальной инженерии, распознавание фишинговых писем и защита от манипуляций.',
    flow_id: 'flow-2',
    is_active: true,
    created_at: '2025-02-01T00:00:00Z',
    updated_at: '2025-03-20T10:00:00Z',
    deleted_at: null,
  },
  {
    id: 'mod-3',
    title: 'Продвинутые техники пентеста',
    description: 'Глубокое погружение в техники тестирования на проникновение для продвинутых пользователей.',
    flow_id: 'flow-3',
    is_active: false,
    created_at: '2025-03-01T00:00:00Z',
    updated_at: '2025-03-01T00:00:00Z',
    deleted_at: null,
  },
];

// Missions
export const missions: Mission[] = [
  {
    id: 'mission-1',
    module_id: 'mod-1',
    code: 'M1-INTRO',
    title: 'Знакомство с угрозами',
    description: 'Изучите основные типы киберугроз и их характеристики',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'mission-2',
    module_id: 'mod-1',
    code: 'M1-DEFENSE',
    title: 'Базовая защита',
    description: 'Освойте базовые методы защиты информации',
    created_at: '2025-01-05T00:00:00Z',
    updated_at: '2025-01-05T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'mission-3',
    module_id: 'mod-2',
    code: 'M2-PHISH',
    title: 'Распознай фишинг',
    description: 'Научитесь определять фишинговые атаки',
    created_at: '2025-02-01T00:00:00Z',
    updated_at: '2025-02-01T00:00:00Z',
    deleted_at: null,
  },
];

// Flows
export const flows: Flow[] = [
  {
    id: 'flow-1',
    module_branch_id: null,
    langflow_flow_id: 'langflow-basics-001',
    title: 'Поток: Основы ИБ',
    description: 'Основной обучающий поток модуля базовой безопасности',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'flow-2',
    module_branch_id: null,
    langflow_flow_id: 'langflow-phishing-001',
    title: 'Поток: Социальная инженерия',
    description: 'Обучающий поток по социальной инженерии',
    created_at: '2025-02-01T00:00:00Z',
    updated_at: '2025-02-01T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'flow-3',
    module_branch_id: null,
    langflow_flow_id: 'langflow-pentest-001',
    title: 'Поток: Пентест',
    description: 'Продвинутый поток по пентесту',
    created_at: '2025-03-01T00:00:00Z',
    updated_at: '2025-03-01T00:00:00Z',
    deleted_at: null,
  },
];

// Lessons
export const lessons: Lesson[] = [
  {
    id: 'lesson-1',
    flow_id: 'flow-1',
    type: 'theory',
    title: 'Что такое информационная безопасность?',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'lesson-2',
    flow_id: 'flow-1',
    type: 'theory',
    title: 'Виды киберугроз',
    created_at: '2025-01-02T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'lesson-3',
    flow_id: 'flow-2',
    type: 'practice',
    title: 'Анализ фишинговых писем',
    created_at: '2025-02-01T00:00:00Z',
    updated_at: '2025-02-01T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'lesson-4',
    flow_id: 'flow-2',
    type: 'video',
    title: 'Психология манипуляций',
    created_at: '2025-02-02T00:00:00Z',
    updated_at: '2025-02-02T00:00:00Z',
    deleted_at: null,
  },
];

// Tasks
export const tasks: Task[] = [
  {
    id: 'task-1',
    module_id: 'mod-1',
    flow_id: 'flow-1',
    title: 'Тест: Основы ИБ',
    type: 'quiz',
    description: 'Проверьте свои знания базовых концепций информационной безопасности',
    max_score: 100,
    achievement_badge: '🛡️ Защитник',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'task-2',
    module_id: 'mod-1',
    flow_id: 'flow-1',
    title: 'Практика: Настройка файрвола',
    type: 'practice',
    description: 'Настройте базовые правила файрвола для защиты системы',
    max_score: 150,
    achievement_badge: '🔥 Огненная стена',
    created_at: '2025-01-05T00:00:00Z',
    updated_at: '2025-01-05T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'task-3',
    module_id: 'mod-1',
    flow_id: 'flow-1',
    title: 'Теория: Криптография',
    type: 'theory',
    description: 'Изучите основы криптографии и шифрования данных',
    max_score: 50,
    achievement_badge: null,
    created_at: '2025-01-10T00:00:00Z',
    updated_at: '2025-01-10T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'task-4',
    module_id: 'mod-2',
    flow_id: 'flow-2',
    title: 'Тест: Распознай фишинг',
    type: 'quiz',
    description: 'Определите фишинговые письма среди обычных',
    max_score: 100,
    achievement_badge: '🎣 Антифишер',
    created_at: '2025-02-01T00:00:00Z',
    updated_at: '2025-02-01T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'task-5',
    module_id: 'mod-2',
    flow_id: 'flow-2',
    title: 'Практика: Анализ атаки',
    type: 'practice',
    description: 'Проанализируйте реальную фишинговую атаку',
    max_score: 200,
    achievement_badge: '🔍 Детектив',
    created_at: '2025-02-05T00:00:00Z',
    updated_at: '2025-02-05T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'task-6',
    module_id: 'mod-2',
    flow_id: 'flow-2',
    title: 'Теория: Социальная инженерия',
    type: 'theory',
    description: 'Узнайте о психологических техниках манипуляций',
    max_score: 50,
    achievement_badge: null,
    created_at: '2025-02-10T00:00:00Z',
    updated_at: '2025-02-10T00:00:00Z',
    deleted_at: null,
  },
];

// User Task Progress
export const userTaskProgress: UserTaskProgress[] = [
  {
    id: 'progress-1',
    user_id: 'user-2',
    task_id: 'task-1',
    status: 'completed',
    score: 85,
    started_at: '2025-03-01T10:00:00Z',
    completed_at: '2025-03-01T10:45:00Z',
    created_at: '2025-03-01T10:00:00Z',
    updated_at: '2025-03-01T10:45:00Z',
    deleted_at: null,
  },
  {
    id: 'progress-2',
    user_id: 'user-2',
    task_id: 'task-2',
    status: 'in_progress',
    score: null,
    started_at: '2025-03-02T14:00:00Z',
    completed_at: null,
    created_at: '2025-03-02T14:00:00Z',
    updated_at: '2025-03-02T14:00:00Z',
    deleted_at: null,
  },
  {
    id: 'progress-3',
    user_id: 'user-3',
    task_id: 'task-1',
    status: 'completed',
    score: 92,
    started_at: '2025-03-05T09:00:00Z',
    completed_at: '2025-03-05T09:30:00Z',
    created_at: '2025-03-05T09:00:00Z',
    updated_at: '2025-03-05T09:30:00Z',
    deleted_at: null,
  },
];

// Assistant Profiles
export const assistantProfiles: AssistantProfile[] = [
  {
    id: 'assistant-1',
    module_id: 'mod-1',
    name: 'SecurityBot',
    system_prompt:
      'Вы — эксперт по информационной безопасности. Помогайте студентам понять базовые концепции ИБ простым языком.',
    capabilities_json: {
      can_explain: true,
      can_quiz: true,
      can_provide_hints: true,
    },
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    deleted_at: null,
  },
  {
    id: 'assistant-2',
    module_id: 'mod-2',
    name: 'PhishGuard',
    system_prompt:
      'Вы — специалист по социальной инженерии. Обучайте распознаванию фишинга и манипуляций.',
    capabilities_json: {
      can_explain: true,
      can_simulate_attacks: true,
      can_analyze_emails: true,
    },
    created_at: '2025-02-01T00:00:00Z',
    updated_at: '2025-02-01T00:00:00Z',
    deleted_at: null,
  },
];

// Chat Sessions
export const chatSessions: ChatSession[] = [
  {
    id: 'session-1',
    user_id: 'user-2',
    module_id: 'mod-1',
    flow_id: 'flow-1',
    started_at: '2025-03-10T15:00:00Z',
    ended_at: null,
    created_at: '2025-03-10T15:00:00Z',
    updated_at: '2025-03-10T15:30:00Z',
    deleted_at: null,
  },
];

// Messages
export const messages: Message[] = [
  {
    id: 'msg-1',
    chat_session_id: 'session-1',
    sender_type: 'system',
    content: 'Добро пожаловать в чат с SecurityBot! Задавайте вопросы по модулю "Основы ИБ".',
    created_at: '2025-03-10T15:00:00Z',
    updated_at: '2025-03-10T15:00:00Z',
  },
  {
    id: 'msg-2',
    chat_session_id: 'session-1',
    sender_type: 'user',
    content: 'Привет! Что такое фаервол и зачем он нужен?',
    created_at: '2025-03-10T15:01:00Z',
    updated_at: '2025-03-10T15:01:00Z',
  },
  {
    id: 'msg-3',
    chat_session_id: 'session-1',
    sender_type: 'assistant',
    content:
      'Привет! Файрвол (firewall) — это система безопасности, которая контролирует входящий и исходящий сетевой трафик. Представь его как охранника на входе в здание: он проверяет каждого посетителя и решает, пропустить его или нет.\n\nФайрвол нужен для:\n- Защиты от несанкционированного доступа\n- Блокировки вредоносного трафика\n- Контроля приложений, использующих сеть',
    created_at: '2025-03-10T15:01:30Z',
    updated_at: '2025-03-10T15:01:30Z',
  },
  {
    id: 'msg-4',
    chat_session_id: 'session-1',
    sender_type: 'user',
    content: 'Спасибо! А какие бывают типы файрволов?',
    created_at: '2025-03-10T15:02:00Z',
    updated_at: '2025-03-10T15:02:00Z',
  },
  {
    id: 'msg-5',
    chat_session_id: 'session-1',
    sender_type: 'assistant',
    content:
      'Основные типы файрволов:\n\n1. **Пакетные фильтры** — анализируют заголовки пакетов (IP, порты)\n2. **Stateful файрволы** — отслеживают состояние соединений\n3. **Application-level** — работают на уровне приложений (HTTP, FTP)\n4. **Next-gen (NGFW)** — объединяют все функции + IPS, антивирус\n\nВ домашних условиях обычно достаточно встроенного файрвола ОС. В корпоративной среде используют более продвинутые решения.',
    created_at: '2025-03-10T15:02:30Z',
    updated_at: '2025-03-10T15:02:30Z',
  },
];

// Helper to generate IDs
let idCounter = 1000;
export const generateId = (prefix: string) => `${prefix}-${++idCounter}`;

