import { apiClient } from './client';
import type {
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
  LoginRequest,
  LoginCredentials,
  RegisterRequest,
  TokenResponse,
  UserResponse,
  CreateProgressRequest,
  UpdateProgressRequest,
  CreateChatSessionRequest,
  CreateMessageRequest,
  CreateModuleRequest,
  UpdateModuleRequest,
  CreateTaskRequest,
  UpdateTaskRequest,
  CreateAssistantProfileRequest,
  UpdateAssistantProfileRequest,
  AttackSession,
  CreateAttackSessionRequest,
  AttackChatResponse,
  AttackEvaluationResponse,
} from './types';

// Auth / Session
export const authApi = {
  // Real authentication
  loginWithCredentials: (data: LoginCredentials) =>
    apiClient.post<TokenResponse>('/api/login', data),
  register: (data: RegisterRequest) =>
    apiClient.post<UserResponse>('/api/register', data),
  me: () => apiClient.get<UserWithRole>('/api/me'),
  // Demo login (by user_id selection)
  demoLogin: (data: LoginRequest) => apiClient.post<UserWithRole>('/api/demo-login', data),
  getUsers: () => apiClient.get<UserWithRole[]>('/api/users'),
};

// Modules / Content
export const modulesApi = {
  getAll: () => apiClient.get<Module[]>('/api/modules'),
  getById: (id: string) => apiClient.get<Module>(`/api/modules/${id}`),
  create: (data: CreateModuleRequest) => apiClient.post<Module>('/api/modules', data),
  update: (id: string, data: UpdateModuleRequest) =>
    apiClient.patch<Module>(`/api/modules/${id}`, data),
  delete: (id: string) => apiClient.delete<void>(`/api/modules/${id}`),
};

export const missionsApi = {
  getByModuleId: (moduleId: string) =>
    apiClient.get<Mission[]>('/api/missions', { module_id: moduleId }),
};

export const flowsApi = {
  getByModuleId: (moduleId: string) =>
    apiClient.get<Flow[]>('/api/flows', { module_id: moduleId }),
  getById: (id: string) => apiClient.get<Flow>(`/api/flows/${id}`),
};

export const lessonsApi = {
  getByFlowId: (flowId: string) =>
    apiClient.get<Lesson[]>('/api/lessons', { flow_id: flowId }),
};

export const tasksApi = {
  getByModuleId: (moduleId: string, flowId?: string) => {
    const params: Record<string, string> = { module_id: moduleId };
    if (flowId) params.flow_id = flowId;
    return apiClient.get<Task[]>('/api/tasks', params);
  },
  getAll: () => apiClient.get<Task[]>('/api/tasks'),
  getById: (id: string) => apiClient.get<Task>(`/api/tasks/${id}`),
  create: (data: CreateTaskRequest) => apiClient.post<Task>('/api/tasks', data),
  update: (id: string, data: UpdateTaskRequest) =>
    apiClient.patch<Task>(`/api/tasks/${id}`, data),
  delete: (id: string) => apiClient.delete<void>(`/api/tasks/${id}`),
};

// Progress
export const progressApi = {
  getByUser: (userId: string, moduleId?: string) => {
    const params: Record<string, string> = { user_id: userId };
    if (moduleId) params.module_id = moduleId;
    return apiClient.get<UserTaskProgress[]>('/api/user_task_progress', params);
  },
  create: (data: CreateProgressRequest) =>
    apiClient.post<UserTaskProgress>('/api/user_task_progress', data),
  update: (id: string, data: UpdateProgressRequest) =>
    apiClient.patch<UserTaskProgress>(`/api/user_task_progress/${id}`, data),
};

// Chat
export const chatApi = {
  getSessions: (userId: string, moduleId?: string, flowId?: string) => {
    const params: Record<string, string> = { user_id: userId };
    if (moduleId) params.module_id = moduleId;
    if (flowId) params.flow_id = flowId;
    return apiClient.get<ChatSession[]>('/api/chat_sessions', params);
  },
  createSession: (data: CreateChatSessionRequest) =>
    apiClient.post<ChatSession>('/api/chat_sessions', data),
  endSession: (id: string) =>
    apiClient.patch<ChatSession>(`/api/chat_sessions/${id}`, { ended_at: new Date().toISOString() }),
  getMessages: (chatSessionId: string) =>
    apiClient.get<Message[]>('/api/messages', { chat_session_id: chatSessionId }),
  sendMessage: (data: CreateMessageRequest) =>
    apiClient.post<Message>('/api/messages', data),
};

// Assistant Profiles
export const assistantsApi = {
  getByModuleId: (moduleId: string) =>
    apiClient.get<AssistantProfile[]>('/api/assistant_profiles', { module_id: moduleId }),
  getAll: () => apiClient.get<AssistantProfile[]>('/api/assistant_profiles'),
  getById: (id: string) => apiClient.get<AssistantProfile>(`/api/assistant_profiles/${id}`),
  create: (data: CreateAssistantProfileRequest) =>
    apiClient.post<AssistantProfile>('/api/assistant_profiles', data),
  update: (id: string, data: UpdateAssistantProfileRequest) =>
    apiClient.patch<AssistantProfile>(`/api/assistant_profiles/${id}`, data),
  delete: (id: string) => apiClient.delete<void>(`/api/assistant_profiles/${id}`),
};

// Attack Sessions - for LangFlow chat in attack tasks
export const attackSessionsApi = {
  getAll: (userId: string, taskId?: string) => {
    const params: Record<string, string> = { user_id: userId };
    if (taskId) params.task_id = taskId;
    return apiClient.get<AttackSession[]>('/api/attack_sessions', params);
  },
  getById: (sessionId: string) =>
    apiClient.get<AttackSession>(`/api/attack_sessions/${sessionId}`),
  create: (data: CreateAttackSessionRequest) =>
    apiClient.post<AttackSession>('/api/attack_sessions', data),
  sendMessage: (sessionId: string, content: string) =>
    apiClient.post<AttackChatResponse>(
      `/api/attack_sessions/${sessionId}/chat`,
      { content }
    ),
  end: (sessionId: string) =>
    apiClient.post<AttackSession>(`/api/attack_sessions/${sessionId}/end`, {}),
  evaluate: (sessionId: string) =>
    apiClient.post<AttackEvaluationResponse>(
      `/api/attack_sessions/${sessionId}/evaluate`,
      {}
    ),
};

