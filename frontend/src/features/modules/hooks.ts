import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { modulesApi, missionsApi, flowsApi, lessonsApi, tasksApi, assistantsApi } from '@/api/endpoints';
import type {
  CreateModuleRequest,
  UpdateModuleRequest,
  CreateTaskRequest,
  UpdateTaskRequest,
  CreateAssistantProfileRequest,
  UpdateAssistantProfileRequest,
} from '@/api/types';

// Query keys
export const moduleKeys = {
  all: ['modules'] as const,
  lists: () => [...moduleKeys.all, 'list'] as const,
  list: (filters?: Record<string, unknown>) => [...moduleKeys.lists(), filters] as const,
  details: () => [...moduleKeys.all, 'detail'] as const,
  detail: (id: string) => [...moduleKeys.details(), id] as const,
};

export const missionKeys = {
  all: ['missions'] as const,
  byModule: (moduleId: string) => [...missionKeys.all, 'module', moduleId] as const,
};

export const flowKeys = {
  all: ['flows'] as const,
  byModule: (moduleId: string) => [...flowKeys.all, 'module', moduleId] as const,
  detail: (id: string) => [...flowKeys.all, 'detail', id] as const,
};

export const lessonKeys = {
  all: ['lessons'] as const,
  byFlow: (flowId: string) => [...lessonKeys.all, 'flow', flowId] as const,
};

export const taskKeys = {
  all: ['tasks'] as const,
  lists: () => [...taskKeys.all, 'list'] as const,
  byModule: (moduleId: string, flowId?: string) =>
    [...taskKeys.all, 'module', moduleId, flowId] as const,
  detail: (id: string) => [...taskKeys.all, 'detail', id] as const,
};

export const assistantKeys = {
  all: ['assistants'] as const,
  lists: () => [...assistantKeys.all, 'list'] as const,
  byModule: (moduleId: string) => [...assistantKeys.all, 'module', moduleId] as const,
  detail: (id: string) => [...assistantKeys.all, 'detail', id] as const,
};

// Modules hooks
export function useModules() {
  return useQuery({
    queryKey: moduleKeys.lists(),
    queryFn: () => modulesApi.getAll(),
  });
}

export function useActiveModules() {
  return useQuery({
    queryKey: moduleKeys.list({ active: true }),
    queryFn: async () => {
      const modules = await modulesApi.getAll();
      return modules.filter((m) => m.is_active && m.deleted_at === null);
    },
  });
}

export function useModule(id: string) {
  return useQuery({
    queryKey: moduleKeys.detail(id),
    queryFn: () => modulesApi.getById(id),
    enabled: !!id,
  });
}

export function useCreateModule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateModuleRequest) => modulesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: moduleKeys.all });
    },
  });
}

export function useUpdateModule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateModuleRequest }) =>
      modulesApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: moduleKeys.all });
      queryClient.invalidateQueries({ queryKey: moduleKeys.detail(id) });
    },
  });
}

export function useDeleteModule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => modulesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: moduleKeys.all });
    },
  });
}

// Missions hooks
export function useMissions(moduleId: string) {
  return useQuery({
    queryKey: missionKeys.byModule(moduleId),
    queryFn: () => missionsApi.getByModuleId(moduleId),
    enabled: !!moduleId,
  });
}

// Flows hooks
export function useFlows(moduleId: string) {
  return useQuery({
    queryKey: flowKeys.byModule(moduleId),
    queryFn: () => flowsApi.getByModuleId(moduleId),
    enabled: !!moduleId,
  });
}

export function useFlow(id: string) {
  return useQuery({
    queryKey: flowKeys.detail(id),
    queryFn: () => flowsApi.getById(id),
    enabled: !!id,
  });
}

// Lessons hooks
export function useLessons(flowId: string) {
  return useQuery({
    queryKey: lessonKeys.byFlow(flowId),
    queryFn: () => lessonsApi.getByFlowId(flowId),
    enabled: !!flowId,
  });
}

// Tasks hooks
export function useTasks(moduleId: string, flowId?: string) {
  return useQuery({
    queryKey: taskKeys.byModule(moduleId, flowId),
    queryFn: () => tasksApi.getByModuleId(moduleId, flowId),
    enabled: !!moduleId,
  });
}

export function useAllTasks() {
  return useQuery({
    queryKey: taskKeys.lists(),
    queryFn: () => tasksApi.getAll(),
  });
}

export function useTask(id: string) {
  return useQuery({
    queryKey: taskKeys.detail(id),
    queryFn: () => tasksApi.getById(id),
    enabled: !!id,
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateTaskRequest) => tasksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.all });
    },
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateTaskRequest }) =>
      tasksApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.all });
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(id) });
    },
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => tasksApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.all });
    },
  });
}

// Assistants hooks
export function useAssistants(moduleId: string) {
  return useQuery({
    queryKey: assistantKeys.byModule(moduleId),
    queryFn: () => assistantsApi.getByModuleId(moduleId),
    enabled: !!moduleId,
  });
}

export function useAllAssistants() {
  return useQuery({
    queryKey: assistantKeys.lists(),
    queryFn: () => assistantsApi.getAll(),
  });
}

export function useAssistant(id: string) {
  return useQuery({
    queryKey: assistantKeys.detail(id),
    queryFn: () => assistantsApi.getById(id),
    enabled: !!id,
  });
}

export function useCreateAssistant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateAssistantProfileRequest) => assistantsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assistantKeys.all });
    },
  });
}

export function useUpdateAssistant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateAssistantProfileRequest }) =>
      assistantsApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: assistantKeys.all });
      queryClient.invalidateQueries({ queryKey: assistantKeys.detail(id) });
    },
  });
}

export function useDeleteAssistant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => assistantsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assistantKeys.all });
    },
  });
}

