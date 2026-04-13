import { useState } from 'react';
import { Plus, Pencil, Trash2, Eye, EyeOff } from 'lucide-react';
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
  useModules,
  useCreateModule,
  useUpdateModule,
  useDeleteModule,
} from '@/features';
import { formatDateShort } from '@/shared/lib/utils';
import type { Module } from '@/api/types';

const moduleSchema = z.object({
  title: z.string().min(1, 'Название обязательно'),
  description: z.string().min(1, 'Описание обязательно'),
  is_active: z.boolean().default(true),
});

type ModuleFormData = z.infer<typeof moduleSchema>;

function ModuleForm({
  module,
  onSubmit,
  onCancel,
  isLoading,
}: {
  module?: Module;
  onSubmit: (data: ModuleFormData) => void;
  onCancel: () => void;
  isLoading: boolean;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ModuleFormData>({
    resolver: zodResolver(moduleSchema),
    defaultValues: {
      title: module?.title || '',
      description: module?.description || '',
      is_active: module?.is_active ?? true,
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="title">Название</Label>
        <Input
          id="title"
          {...register('title')}
          placeholder="Введите название модуля"
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
          placeholder="Введите описание модуля"
          rows={4}
        />
        {errors.description && (
          <p className="text-sm text-destructive">{errors.description.message}</p>
        )}
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_active"
          {...register('is_active')}
          className="accent-primary"
        />
        <Label htmlFor="is_active">Активен</Label>
      </div>

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Отмена
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading && <Spinner size="sm" className="mr-2" />}
          {module ? 'Сохранить' : 'Создать'}
        </Button>
      </DialogFooter>
    </form>
  );
}

export function AdminModulesPage() {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingModule, setEditingModule] = useState<Module | null>(null);

  const { data: modules, isLoading } = useModules();
  const createModule = useCreateModule();
  const updateModule = useUpdateModule();
  const deleteModule = useDeleteModule();

  const handleCreate = async (data: ModuleFormData) => {
    await createModule.mutateAsync(data);
    setIsCreateOpen(false);
  };

  const handleUpdate = async (data: ModuleFormData) => {
    if (!editingModule) return;
    await updateModule.mutateAsync({ id: editingModule.id, data });
    setEditingModule(null);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Вы уверены, что хотите удалить этот модуль?')) return;
    await deleteModule.mutateAsync(id);
  };

  const handleToggleActive = async (module: Module) => {
    await updateModule.mutateAsync({
      id: module.id,
      data: { is_active: !module.is_active },
    });
  };

  if (isLoading) {
    return <LoadingScreen />;
  }

  const activeModules = modules?.filter((m) => m.deleted_at === null) || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Управление модулями</h2>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Добавить модуль
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Новый модуль</DialogTitle>
              <DialogDescription>
                Создайте новый обучающий модуль
              </DialogDescription>
            </DialogHeader>
            <ModuleForm
              onSubmit={handleCreate}
              onCancel={() => setIsCreateOpen(false)}
              isLoading={createModule.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      {activeModules.length > 0 ? (
        <div className="space-y-4">
          {activeModules.map((module) => (
            <Card key={module.id}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{module.title}</h3>
                      <Badge variant={module.is_active ? 'success' : 'outline'}>
                        {module.is_active ? 'Активен' : 'Неактивен'}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                      {module.description}
                    </p>
                    <p className="text-xs text-muted-foreground mt-2">
                      Создан: {formatDateShort(module.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleToggleActive(module)}
                      aria-label={module.is_active ? 'Деактивировать' : 'Активировать'}
                    >
                      {module.is_active ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setEditingModule(module)}
                      aria-label="Редактировать"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(module.id)}
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
          title="Нет модулей"
          description="Создайте первый обучающий модуль"
          action={{
            label: 'Добавить модуль',
            onClick: () => setIsCreateOpen(true),
          }}
        />
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editingModule} onOpenChange={() => setEditingModule(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Редактировать модуль</DialogTitle>
            <DialogDescription>
              Измените параметры модуля
            </DialogDescription>
          </DialogHeader>
          {editingModule && (
            <ModuleForm
              module={editingModule}
              onSubmit={handleUpdate}
              onCancel={() => setEditingModule(null)}
              isLoading={updateModule.isPending}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

