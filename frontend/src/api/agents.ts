import { apiClient } from './client';
import type {
  TutorChatRequest,
  TutorChatResponse,
  EvaluateTaskRequest,
  EvaluateTaskResponse,
} from './types';

/**
 * Chat with tutor agent for help.
 */
export async function chatWithTutor(request: TutorChatRequest): Promise<TutorChatResponse> {
  return apiClient.post<TutorChatResponse>('/api/agents/tutor/chat', request);
}

/**
 * Evaluate student's task submission.
 */
export async function evaluateTask(request: EvaluateTaskRequest): Promise<EvaluateTaskResponse> {
  return apiClient.post<EvaluateTaskResponse>('/api/agents/evaluator/evaluate', request);
}

