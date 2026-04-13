import { useState } from 'react';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Textarea } from '@/shared/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/shared/ui/dialog';
import { LoadingScreen, Spinner } from '@/shared/ui/spinner';
import { EmptyState } from '@/shared/ui/empty-state';
import {
  useAllTasks,
  useModules,
  useCreateTask,
  useUpdateTask,
  useDeleteTask,
} from '@/features';
import { TASK_TYPE_LABELS } from '@/shared/constants';
import type { Task, CreateTaskRequest } from '@/api/types';

const taskSchema = z.object({
  title: z.string().min(1, 'Название обязательно'),
  description: z.string().min(1, 'Описание обязательно'),
  module_id: z.string().min(1, 'Выберите модуль'),
  type: z.string().min(1, 'Выберите тип'),
  max_score: z.coerce.number().min(1, 'Минимум 1 балл'),
  achievement_badge: z.string().optional(),
});

type TaskFormData = z.infer<typeof taskSchema>;

function TaskForm({
  task,
  modules,
  onSubmit,
  onCancel,
  isLoading,
}: {
  task?: Task;
  modules: { id: string; title: string }[];
  onSubmit: (data: TaskFormData) => void;
  onCancel: () => void;
  isLoading: boolean;
}) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<TaskFormData>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      title: task?.title || '',
      description: task?.description || '',
      module_id: task?.module_id || '',
      type: task?.type || 'theory',
      max_score: task?.max_score || 100,
      achievement_badge: task?.achievement_badge || '',
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="title">Название</Label>
        <Input
          id="title"
          {...register('title')}
          placeholder="Введите название задания"
        />
        {errors.title && (
          <p className="text-sm text-destructive">{errors.title.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Описание</Label>
        <Textarea
          id="description"
          {...register('description')}
          placeholder="Введите описание задания"
          rows={3}
        />
        {errors.description && (
          <p className="text-sm text-destructive">{errors.description.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Модуль</Label>
          <Select
            value={watch('module_id')}
            onValueChange={(value) => setValue('module_id', value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Выберите модуль" />
            </SelectTrigger>
            <SelectContent>
              {modules.map((module) => (
                <SelectItem key={module.id} value={module.id}>
                  {module.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors.module_id && (
            <p className="text-sm text-destructive">{errors.module_id.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label>Тип</Label>
          <Select
            value={watch('type')}
            onValueChange={(value) => setValue('type', value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Выберите тип" />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(TASK_TYPE_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors.type && (
            <p className="text-sm text-destructive">{errors.type.message}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="max_score">Максимальный балл</Label>
          <Input
            id="max_score"
            type="number"
            {...register('max_score')}
            min={1}
          />
          {errors.max_score && (
            <p className="text-sm text-destructive">{errors.max_score.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="achievement_badge">Бейдж (emoji)</Label>
          <Input
            id="achievement_badge"
            {...register('achievement_badge')}
            placeholder="🏆"
          />
        </div>
      </div>

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Отмена
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading && <Spinner size="sm" className="mr-2" />}
          {task ? 'Сохранить' : 'Создать'}
        </Button>
      </DialogFooter>
    </form>
  );
}

export function AdminTasksPage() {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);

  const { data: tasks, isLoading: tasksLoading } = useAllTasks();
  const { data: modules = [] } = useModules();
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

  const handleCreate = async (data: TaskFormData) => {
    await createTask.mutateAsync({
      ...data,
      achievement_badge: data.achievement_badge || null,
    } as CreateTaskRequest);
    setIsCreateOpen(false);
  };

  const handleUpdate = async (data: TaskFormData) => {
    if (!editingTask) return;
    await updateTask.mutateAsync({
      id: editingTask.id,
      data: {
        ...data,
        achievement_badge: data.achievement_badge || null,
      },
    });
    setEditingTask(null);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Вы уверены, что хотите удалить это задание?')) return;
    await deleteTask.mutateAsync(id);
  };

  if (tasksLoading) {
    return <LoadingScreen />;
  }

  const activeTasks = tasks?.filter((t) => t.deleted_at === null) || [];
  const moduleMap = new Map(modules.map((m) => [m.id, m.title]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Управление заданиями</h2>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Добавить задание
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Новое задание</DialogTitle>
              <DialogDescription>
                Создайте новое задание для модуля
              </DialogDescription>
            </DialogHeader>
            <TaskForm
              modules={modules.filter((m) => m.deleted_at === null)}
              onSubmit={handleCreate}
              onCancel={() => setIsCreateOpen(false)}
              isLoading={createTask.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      {activeTasks.length > 0 ? (
        <div className="space-y-4">
          {activeTasks.map((task) => (
            <Card key={task.id}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold">{task.title}</h3>
                      {task.achievement_badge && (
                        <span className="text-lg">{task.achievement_badge}</span>
                      )}
                      <Badge variant="outline">
                        {TASK_TYPE_LABELS[task.type] || task.type}
                      </Badge>
                      <Badge variant="secondary">
                        {task.max_score} баллов
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                      {task.description}
                    </p>
                    <p className="text-xs text-muted-foreground mt-2">
                      Модуль: {moduleMap.get(task.module_id) || task.module_id}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setEditingTask(task)}
                      aria-label="Редактировать"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(task.id)}
                      aria-label="Удалить"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          title="Нет заданий"
          description="Создайте первое задание"
          action={{
            label: 'Добавить задание',
            onClick: () => setIsCreateOpen(true),
          }}
        />
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editingTask} onOpenChange={() => setEditingTask(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Редактировать задание</DialogTitle>
            <DialogDescription>
              Измените параметры задания
            </DialogDescription>
          </DialogHeader>
          {editingTask && (
            <TaskForm
              task={editingTask}
              modules={modules.filter((m) => m.deleted_at === null)}
              onSubmit={handleUpdate}
              onCancel={() => setEditingTask(null)}
              isLoading={updateTask.isPending}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

