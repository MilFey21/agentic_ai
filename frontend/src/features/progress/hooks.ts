import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { progressApi } from '@/api/endpoints';
import type { CreateProgressRequest, UpdateProgressRequest } from '@/api/types';
import { useCurrentUser } from '@/features/auth/store';

export const progressKeys = {
  all: ['progress'] as const,
  byUser: (userId: string, moduleId?: string) =>
    [...progressKeys.all, 'user', userId, moduleId] as const,
};

export function useUserProgress(moduleId?: string) {
  const user = useCurrentUser();

  return useQuery({
    queryKey: progressKeys.byUser(user?.id ?? '', moduleId),
    queryFn: () => progressApi.getByUser(user!.id, moduleId),
    enabled: !!user?.id,
  });
}

export function useProgressByUser(userId: string, moduleId?: string) {
  return useQuery({
    queryKey: progressKeys.byUser(userId, moduleId),
    queryFn: () => progressApi.getByUser(userId, moduleId),
    enabled: !!userId,
  });
}

export function useCreateProgress() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateProgressRequest) => progressApi.create(data),
    onSuccess: (newProgress, data) => {
      // Optimistically update the cache with the new progress
      queryClient.setQueryData<typeof newProgress[]>(
        progressKeys.byUser(data.user_id),
        (old) => old ? [...old, newProgress] : [newProgress]
      );
      // Also update with module_id if it exists in task
      queryClient.invalidateQueries({
        queryKey: progressKeys.byUser(data.user_id),
      });
    },
  });
}

export function useUpdateProgress() {
  const queryClient = useQueryClient();
  const user = useCurrentUser();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateProgressRequest }) =>
      progressApi.update(id, data),
    onSuccess: () => {
      if (user?.id) {
        queryClient.invalidateQueries({
          queryKey: progressKeys.byUser(user.id),
        });
      }
    },
  });
}

// Helper hook to start a task
export function useStartTask() {
  const createProgress = useCreateProgress();
  const user = useCurrentUser();

  return async (taskId: string) => {
    if (!user) throw new Error('User not authenticated');

    return createProgress.mutateAsync({
      user_id: user.id,
      task_id: taskId,
      status: 'in_progress',
      started_at: new Date().toISOString(),
    });
  };
}

// Helper hook to complete a task
export function useCompleteTask() {
  const updateProgress = useUpdateProgress();

  return async (progressId: string, score?: number) => {
    return updateProgress.mutateAsync({
      id: progressId,
      data: {
        status: 'completed',
        score: score ?? null,
        completed_at: new Date().toISOString(),
      },
    });
  };
}

