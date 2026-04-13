import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatApi } from '@/api/endpoints';
import type { CreateChatSessionRequest, CreateMessageRequest, Message } from '@/api/types';
import { useCurrentUser } from '@/features/auth/store';

export const chatKeys = {
  all: ['chat'] as const,
  sessions: (userId: string, moduleId?: string, flowId?: string) =>
    [...chatKeys.all, 'sessions', userId, moduleId, flowId] as const,
  messages: (sessionId: string) => [...chatKeys.all, 'messages', sessionId] as const,
};

export function useChatSessions(moduleId?: string, flowId?: string) {
  const user = useCurrentUser();

  return useQuery({
    queryKey: chatKeys.sessions(user?.id ?? '', moduleId, flowId),
    queryFn: () => chatApi.getSessions(user!.id, moduleId, flowId),
    enabled: !!user?.id,
  });
}

export function useActiveSession(moduleId: string, flowId?: string) {
  const { data: sessions } = useChatSessions(moduleId, flowId);

  return sessions?.find((s) => s.ended_at === null) ?? null;
}

export function useCreateOrGetSession() {
  const queryClient = useQueryClient();
  const user = useCurrentUser();

  return useMutation({
    mutationFn: (data: Omit<CreateChatSessionRequest, 'user_id'>) =>
      chatApi.createSession({
        ...data,
        user_id: user!.id,
      }),
    onSuccess: (_, data) => {
      queryClient.invalidateQueries({
        queryKey: chatKeys.sessions(user!.id, data.module_id, data.flow_id ?? undefined),
      });
    },
  });
}

export function useEndSession() {
  const queryClient = useQueryClient();
  const user = useCurrentUser();

  return useMutation({
    mutationFn: (sessionId: string) => chatApi.endSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: chatKeys.sessions(user!.id),
      });
    },
  });
}

export function useMessages(sessionId: string) {
  return useQuery({
    queryKey: chatKeys.messages(sessionId),
    queryFn: () => chatApi.getMessages(sessionId),
    enabled: !!sessionId,
    refetchInterval: 3000, // Poll for new messages
  });
}

export function useSendMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateMessageRequest) => chatApi.sendMessage(data),
    onSuccess: (messages, data) => {
      queryClient.setQueryData<Message[]>(
        chatKeys.messages(data.chat_session_id),
        (oldMessages) => {
          if (!oldMessages) return Array.isArray(messages) ? messages : [messages];
          if (Array.isArray(messages)) {
            return [...oldMessages, ...messages];
          }
          return [...oldMessages, messages];
        }
      );
    },
  });
}

