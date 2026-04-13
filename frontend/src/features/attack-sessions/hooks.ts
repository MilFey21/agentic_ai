import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { attackSessionsApi } from '@/api/endpoints';
import type { CreateAttackSessionRequest, AttackChatMessage } from '@/api/types';
import { useCurrentUser } from '@/features/auth/store';

export const attackSessionKeys = {
  all: ['attack-sessions'] as const,
  byTask: (userId: string, taskId: string) => [...attackSessionKeys.all, 'task', userId, taskId] as const,
  byId: (sessionId: string) => [...attackSessionKeys.all, 'session', sessionId] as const,
  messages: (sessionId: string) => [...attackSessionKeys.all, 'messages', sessionId] as const,
};

export function useAttackSessions(taskId?: string) {
  const user = useCurrentUser();

  return useQuery({
    queryKey: attackSessionKeys.byTask(user?.id ?? '', taskId ?? ''),
    queryFn: () => attackSessionsApi.getAll(user!.id, taskId),
    enabled: !!taskId && !!user?.id,
  });
}

export function useActiveAttackSession(taskId: string) {
  const { data: sessions } = useAttackSessions(taskId);
  return sessions?.find((s) => s.status === 'active') ?? null;
}

export function useAttackSession(sessionId: string) {
  return useQuery({
    queryKey: attackSessionKeys.byId(sessionId),
    queryFn: () => attackSessionsApi.getById(sessionId),
    enabled: !!sessionId,
  });
}

export function useCreateAttackSession() {
  const queryClient = useQueryClient();
  const user = useCurrentUser();

  return useMutation({
    mutationFn: (data: Omit<CreateAttackSessionRequest, 'user_id'>) =>
      attackSessionsApi.create({
        ...data,
        user_id: user!.id,
      }),
    onSuccess: (session) => {
      queryClient.invalidateQueries({
        queryKey: attackSessionKeys.byTask(user!.id, session.task_id),
      });
    },
  });
}

export function useSendAttackMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sessionId,
      content,
    }: {
      sessionId: string;
      content: string;
    }) => attackSessionsApi.sendMessage(sessionId, content),
    onSuccess: (response, { sessionId }) => {
      // Update messages cache optimistically
      queryClient.setQueryData<AttackChatMessage[]>(
        attackSessionKeys.messages(sessionId),
        (oldMessages) => {
          const newMessages = [response.user_message, response.assistant_message];
          if (!oldMessages) return newMessages;
          return [...oldMessages, ...newMessages];
        }
      );
    },
  });
}

export function useEndAttackSession() {
  const queryClient = useQueryClient();
  const user = useCurrentUser();

  return useMutation({
    mutationFn: (sessionId: string) => attackSessionsApi.end(sessionId),
    onSuccess: (session) => {
      if (user?.id) {
        queryClient.invalidateQueries({
          queryKey: attackSessionKeys.byTask(user.id, session.task_id),
        });
      }
      queryClient.invalidateQueries({
        queryKey: attackSessionKeys.byId(session.id),
      });
    },
  });
}

export function useEvaluateAttackSession() {
  return useMutation({
    mutationFn: (sessionId: string) => attackSessionsApi.evaluate(sessionId),
  });
}

// Local state management for chat messages (in-memory during session)
export function useAttackMessages(sessionId: string) {
  return useQuery({
    queryKey: attackSessionKeys.messages(sessionId),
    queryFn: () => [] as AttackChatMessage[],
    enabled: !!sessionId,
    staleTime: Infinity, // Messages are stored in client memory during session
  });
}

