// Entity types matching ERD exactly

export interface Role {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface User {
  id: string;
  role_id: string;
  username: string;
  email: string;
  langflow_user_id: string | null;
  langflow_folder_id: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface UserWithRole extends User {
  role: Role;
}

export interface Module {
  id: string;
  title: string;
  description: string;
  flow_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface Mission {
  id: string;
  module_id: string;
  code: string;
  title: string;
  description: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface Flow {
  id: string;
  module_branch_id: string | null;
  langflow_flow_id: string | null;
  title: string;
  description: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface Lesson {
  id: string;
  flow_id: string;
  type: string;
  title: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface Task {
  id: string;
  module_id: string;
  flow_id: string | null;
  title: string;
  type: string;
  description: string;
  max_score: number;
  achievement_badge: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface UserTaskProgress {
  id: string;
  user_id: string;
  task_id: string;
  status: 'not_started' | 'in_progress' | 'completed' | 'failed';
  score: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface AssistantProfile {
  id: string;
  module_id: string;
  name: string;
  system_prompt: string;
  capabilities_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface ChatSession {
  id: string;
  user_id: string;
  module_id: string;
  flow_id: string | null;
  started_at: string;
  ended_at: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface Message {
  id: string;
  chat_session_id: string;
  sender_type: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  updated_at: string;
}

// API Request/Response types

// Legacy demo login (kept for compatibility)
export interface LoginRequest {
  user_id: string;
}

// Real authentication
export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  username: string;
  email: string;
  roles: string[];
  langflow_user_id: string | null;
  langflow_folder_id: string | null;
  created_at: string;
  updated_at: string | null;
  deleted_at: string | null;
}

export interface CreateProgressRequest {
  user_id: string;
  task_id: string;
  status: UserTaskProgress['status'];
  score?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface UpdateProgressRequest {
  status?: UserTaskProgress['status'];
  score?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface CreateChatSessionRequest {
  user_id: string;
  module_id: string;
  flow_id?: string | null;
}

export interface CreateMessageRequest {
  chat_session_id: string;
  sender_type: Message['sender_type'];
  content: string;
}

export interface CreateModuleRequest {
  title: string;
  description: string;
  flow_id?: string | null;
  is_active?: boolean;
}

export interface UpdateModuleRequest {
  title?: string;
  description?: string;
  flow_id?: string | null;
  is_active?: boolean;
}

export interface CreateTaskRequest {
  module_id: string;
  flow_id?: string | null;
  title: string;
  type: string;
  description: string;
  max_score: number;
  achievement_badge?: string | null;
}

export interface UpdateTaskRequest {
  title?: string;
  type?: string;
  description?: string;
  max_score?: number;
  achievement_badge?: string | null;
}

export interface CreateAssistantProfileRequest {
  module_id: string;
  name: string;
  system_prompt: string;
  capabilities_json?: Record<string, unknown> | null;
}

export interface UpdateAssistantProfileRequest {
  name?: string;
  system_prompt?: string;
  capabilities_json?: Record<string, unknown> | null;
}

// Aggregated types for UI

export interface ModuleWithProgress extends Module {
  totalTasks: number;
  completedTasks: number;
  progress: number;
}

export interface TaskWithProgress extends Task {
  progress: UserTaskProgress | null;
}

// Agents API types

export interface TutorChatRequest {
  task_id: string;
  task_type: string;
  task_title: string;
  task_description: string;
  message: string;
  current_solution?: string | null;
  attack_session_id?: string | null;  // ID attack session для получения диалога с ботом
  chat_history?: Array<{ role: 'user' | 'assistant'; content: string }>;
}

export interface TutorChatResponse {
  response: string;
  help_type?: string | null;
  stage?: string | null;
  tools_used: string[];
}

export interface EvaluateTaskRequest {
  task_id: string;
  task_type: string;
  task_title: string;
  task_description: string;
  max_score: number;
  student_solution: string;
  evaluation_id?: string | null;  // §7.5 идемпотентность — один и тот же ID не вызывает повторный LLM-вызов
  apply_delay?: boolean;          // §3.3 — задержка 30 с перед оценкой (ждём записи всех попыток)
}

export interface EvaluationCriterion {
  name: string;
  score: number;
  max_score: number;
  feedback: string;
}

export interface EvaluateTaskResponse {
  success: boolean;
  score: number;
  max_score: number;
  percentage: number;
  feedback: string;
  criteria: EvaluationCriterion[];
  stage?: string | null;
  recommendations: string[];
}

// Расширенный ответ при оценке через attack session (включает conversation_length)
export interface AttackEvaluationResponse extends EvaluateTaskResponse {
  conversation_length: number;
}

// Attack Sessions types
export interface AttackSession {
  id: string;
  user_id: string;
  task_id: string;
  progress_id: string;
  langflow_flow_id: string;
  langflow_session_id: string | null;
  template_name: string;
  status: 'active' | 'completed' | 'failed';
  started_at: string;
  ended_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface CreateAttackSessionRequest {
  user_id: string;
  task_id: string;
  template_name?: string;
}

export interface AttackChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface AttackChatResponse {
  user_message: AttackChatMessage;
  assistant_message: AttackChatMessage;
}

export interface AttackChatMessageCreate {
  content: string;
}

