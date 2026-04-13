// In-memory database for mock data
import {
  roles,
  users,
  usersWithRoles,
  modules,
  missions,
  flows,
  lessons,
  tasks,
  userTaskProgress,
  assistantProfiles,
  chatSessions,
  messages,
  generateId,
} from './seed';
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

// Mutable copies
export const db = {
  roles: [...roles] as Role[],
  users: [...users] as User[],
  usersWithRoles: [...usersWithRoles] as UserWithRole[],
  modules: [...modules] as Module[],
  missions: [...missions] as Mission[],
  flows: [...flows] as Flow[],
  lessons: [...lessons] as Lesson[],
  tasks: [...tasks] as Task[],
  userTaskProgress: [...userTaskProgress] as UserTaskProgress[],
  assistantProfiles: [...assistantProfiles] as AssistantProfile[],
  chatSessions: [...chatSessions] as ChatSession[],
  messages: [...messages] as Message[],
};

// Current user state (simulating session)
let currentUserId: string | null = null;

export const auth = {
  getCurrentUserId: () => currentUserId,
  setCurrentUserId: (id: string | null) => {
    currentUserId = id;
  },
  getCurrentUser: (): UserWithRole | null => {
    if (!currentUserId) return null;
    return db.usersWithRoles.find((u) => u.id === currentUserId) || null;
  },
};

// Helper functions for data manipulation
export const dbHelpers = {
  // Modules
  getActiveModules: () =>
    db.modules.filter((m) => m.is_active && m.deleted_at === null),
  
  getModuleById: (id: string) =>
    db.modules.find((m) => m.id === id && m.deleted_at === null),

  createModule: (data: Partial<Module>): Module => {
    const now = new Date().toISOString();
    const module: Module = {
      id: generateId('mod'),
      title: data.title || '',
      description: data.description || '',
      flow_id: data.flow_id || null,
      is_active: data.is_active ?? true,
      created_at: now,
      updated_at: now,
      deleted_at: null,
    };
    db.modules.push(module);
    return module;
  },

  updateModule: (id: string, data: Partial<Module>): Module | null => {
    const index = db.modules.findIndex((m) => m.id === id);
    if (index === -1) return null;
    db.modules[index] = {
      ...db.modules[index],
      ...data,
      updated_at: new Date().toISOString(),
    };
    return db.modules[index];
  },

  deleteModule: (id: string): boolean => {
    const module = db.modules.find((m) => m.id === id);
    if (!module) return false;
    module.deleted_at = new Date().toISOString();
    return true;
  },

  // Tasks
  getTasksByModuleId: (moduleId: string, flowId?: string) => {
    return db.tasks.filter(
      (t) =>
        t.module_id === moduleId &&
        t.deleted_at === null &&
        (flowId ? t.flow_id === flowId : true)
    );
  },

  getTaskById: (id: string) =>
    db.tasks.find((t) => t.id === id && t.deleted_at === null),

  createTask: (data: Partial<Task>): Task => {
    const now = new Date().toISOString();
    const task: Task = {
      id: generateId('task'),
      module_id: data.module_id || '',
      flow_id: data.flow_id || null,
      title: data.title || '',
      type: data.type || 'theory',
      description: data.description || '',
      max_score: data.max_score || 100,
      achievement_badge: data.achievement_badge || null,
      created_at: now,
      updated_at: now,
      deleted_at: null,
    };
    db.tasks.push(task);
    return task;
  },

  updateTask: (id: string, data: Partial<Task>): Task | null => {
    const index = db.tasks.findIndex((t) => t.id === id);
    if (index === -1) return null;
    db.tasks[index] = {
      ...db.tasks[index],
      ...data,
      updated_at: new Date().toISOString(),
    };
    return db.tasks[index];
  },

  deleteTask: (id: string): boolean => {
    const task = db.tasks.find((t) => t.id === id);
    if (!task) return false;
    task.deleted_at = new Date().toISOString();
    return true;
  },

  // Progress
  getProgressByUser: (userId: string, moduleId?: string) => {
    let progress = db.userTaskProgress.filter(
      (p) => p.user_id === userId && p.deleted_at === null
    );
    
    if (moduleId) {
      const moduleTasks = db.tasks.filter((t) => t.module_id === moduleId);
      const moduleTaskIds = moduleTasks.map((t) => t.id);
      progress = progress.filter((p) => moduleTaskIds.includes(p.task_id));
    }
    
    return progress;
  },

  getProgressByTaskAndUser: (taskId: string, userId: string) =>
    db.userTaskProgress.find(
      (p) => p.task_id === taskId && p.user_id === userId && p.deleted_at === null
    ),

  createProgress: (data: Partial<UserTaskProgress>): UserTaskProgress => {
    const now = new Date().toISOString();
    const progress: UserTaskProgress = {
      id: generateId('progress'),
      user_id: data.user_id || '',
      task_id: data.task_id || '',
      status: data.status || 'not_started',
      score: data.score ?? null,
      started_at: data.started_at || null,
      completed_at: data.completed_at || null,
      created_at: now,
      updated_at: now,
      deleted_at: null,
    };
    db.userTaskProgress.push(progress);
    return progress;
  },

  updateProgress: (id: string, data: Partial<UserTaskProgress>): UserTaskProgress | null => {
    const index = db.userTaskProgress.findIndex((p) => p.id === id);
    if (index === -1) return null;
    db.userTaskProgress[index] = {
      ...db.userTaskProgress[index],
      ...data,
      updated_at: new Date().toISOString(),
    };
    return db.userTaskProgress[index];
  },

  // Missions
  getMissionsByModuleId: (moduleId: string) =>
    db.missions.filter((m) => m.module_id === moduleId && m.deleted_at === null),

  // Flows
  getFlowsByModuleId: (moduleId: string) => {
    const module = db.modules.find((m) => m.id === moduleId);
    if (!module?.flow_id) return [];
    return db.flows.filter((f) => f.id === module.flow_id && f.deleted_at === null);
  },

  getFlowById: (id: string) =>
    db.flows.find((f) => f.id === id && f.deleted_at === null),

  // Lessons
  getLessonsByFlowId: (flowId: string) =>
    db.lessons.filter((l) => l.flow_id === flowId && l.deleted_at === null),

  // Assistants
  getAssistantsByModuleId: (moduleId: string) =>
    db.assistantProfiles.filter(
      (a) => a.module_id === moduleId && a.deleted_at === null
    ),

  createAssistant: (data: Partial<AssistantProfile>): AssistantProfile => {
    const now = new Date().toISOString();
    const assistant: AssistantProfile = {
      id: generateId('assistant'),
      module_id: data.module_id || '',
      name: data.name || '',
      system_prompt: data.system_prompt || '',
      capabilities_json: data.capabilities_json || null,
      created_at: now,
      updated_at: now,
      deleted_at: null,
    };
    db.assistantProfiles.push(assistant);
    return assistant;
  },

  updateAssistant: (id: string, data: Partial<AssistantProfile>): AssistantProfile | null => {
    const index = db.assistantProfiles.findIndex((a) => a.id === id);
    if (index === -1) return null;
    db.assistantProfiles[index] = {
      ...db.assistantProfiles[index],
      ...data,
      updated_at: new Date().toISOString(),
    };
    return db.assistantProfiles[index];
  },

  deleteAssistant: (id: string): boolean => {
    const assistant = db.assistantProfiles.find((a) => a.id === id);
    if (!assistant) return false;
    assistant.deleted_at = new Date().toISOString();
    return true;
  },

  // Chat Sessions
  getActiveChatSession: (userId: string, moduleId: string, flowId?: string) =>
    db.chatSessions.find(
      (s) =>
        s.user_id === userId &&
        s.module_id === moduleId &&
        (flowId ? s.flow_id === flowId : true) &&
        s.ended_at === null &&
        s.deleted_at === null
    ),

  getChatSessions: (userId: string, moduleId?: string, flowId?: string) =>
    db.chatSessions.filter(
      (s) =>
        s.user_id === userId &&
        s.deleted_at === null &&
        (moduleId ? s.module_id === moduleId : true) &&
        (flowId ? s.flow_id === flowId : true)
    ),

  createChatSession: (data: Partial<ChatSession>): ChatSession => {
    const now = new Date().toISOString();
    const session: ChatSession = {
      id: generateId('session'),
      user_id: data.user_id || '',
      module_id: data.module_id || '',
      flow_id: data.flow_id || null,
      started_at: now,
      ended_at: null,
      created_at: now,
      updated_at: now,
      deleted_at: null,
    };
    db.chatSessions.push(session);
    return session;
  },

  endChatSession: (id: string): ChatSession | null => {
    const session = db.chatSessions.find((s) => s.id === id);
    if (!session) return null;
    session.ended_at = new Date().toISOString();
    session.updated_at = new Date().toISOString();
    return session;
  },

  // Messages
  getMessagesBySessionId: (sessionId: string) =>
    db.messages
      .filter((m) => m.chat_session_id === sessionId)
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()),

  createMessage: (data: Partial<Message>): Message => {
    const now = new Date().toISOString();
    const message: Message = {
      id: generateId('msg'),
      chat_session_id: data.chat_session_id || '',
      sender_type: data.sender_type || 'user',
      content: data.content || '',
      created_at: now,
      updated_at: now,
    };
    db.messages.push(message);
    return message;
  },
};

