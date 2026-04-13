import { useState } from 'react';
import { Plus, Pencil, Trash2, Bot } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
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
  useAllAssistants,
  useModules,
  useCreateAssistant,
  useUpdateAssistant,
  useDeleteAssistant,
} from '@/features';
import type { AssistantProfile, CreateAssistantProfileRequest } from '@/api/types';

const assistantSchema = z.object({
  name: z.string().min(1, 'Имя обязательно'),
  system_prompt: z.string().min(1, 'System prompt обязателен'),
  module_id: z.string().min(1, 'Выберите модуль'),
});

type AssistantFormData = z.infer<typeof assistantSchema>;

function AssistantForm({
  assistant,
  modules,
  onSubmit,
  onCancel,
  isLoading,
}: {
  assistant?: AssistantProfile;
  modules: { id: string; title: string }[];
  onSubmit: (data: AssistantFormData) => void;
  onCancel: () => void;
  isLoading: boolean;
}) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<AssistantFormData>({
    resolver: zodResolver(assistantSchema),
    defaultValues: {
      name: assistant?.name || '',
      system_prompt: assistant?.system_prompt || '',
      module_id: assistant?.module_id || '',
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Имя ассистента</Label>
        <Input
          id="name"
          {...register('name')}
          placeholder="Например: SecurityBot"
        />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name.message}</p>
        )}
      </div>

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
        <Label htmlFor="system_prompt">System Prompt</Label>
        <Textarea
          id="system_prompt"
          {...register('system_prompt')}
          placeholder="Опишите роль и поведение ассистента..."
          rows={6}
        />
        {errors.system_prompt && (
          <p className="text-sm text-destructive">{errors.system_prompt.message}</p>
        )}
      </div>

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Отмена
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading && <Spinner size="sm" className="mr-2" />}
          {assistant ? 'Сохранить' : 'Создать'}
        </Button>
      </DialogFooter>
    </form>
  );
}

export function AdminAssistantsPage() {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingAssistant, setEditingAssistant] = useState<AssistantProfile | null>(null);

  const { data: assistants, isLoading: assistantsLoading } = useAllAssistants();
  const { data: modules = [] } = useModules();
  const createAssistant = useCreateAssistant();
  const updateAssistant = useUpdateAssistant();
  const deleteAssistant = useDeleteAssistant();

  const handleCreate = async (data: AssistantFormData) => {
    await createAssistant.mutateAsync(data as CreateAssistantProfileRequest);
    setIsCreateOpen(false);
  };

  const handleUpdate = async (data: AssistantFormData) => {
    if (!editingAssistant) return;
    await updateAssistant.mutateAsync({
      id: editingAssistant.id,
      data,
    });
    setEditingAssistant(null);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Вы уверены, что хотите удалить этого ассистента?')) return;
    await deleteAssistant.mutateAsync(id);
  };

  if (assistantsLoading) {
    return <LoadingScreen />;
  }

  const activeAssistants = assistants?.filter((a) => a.deleted_at === null) || [];
  const moduleMap = new Map(modules.map((m) => [m.id, m.title]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Управление ассистентами</h2>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Добавить ассистента
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Новый ассистент</DialogTitle>
              <DialogDescription>
                Создайте AI-ассистента для модуля
              </DialogDescription>
            </DialogHeader>
            <AssistantForm
              modules={modules.filter((m) => m.deleted_at === null)}
              onSubmit={handleCreate}
              onCancel={() => setIsCreateOpen(false)}
              isLoading={createAssistant.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      {activeAssistants.length > 0 ? (
        <div className="space-y-4">
          {activeAssistants.map((assistant) => (
            <Card key={assistant.id}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-secondary/10 shrink-0">
                      <Bot className="h-6 w-6 text-secondary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{assistant.name}</h3>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                        {assistant.system_prompt}
                      </p>
                      <p className="text-xs text-muted-foreground mt-2">
                        Модуль: {moduleMap.get(assistant.module_id) || assistant.module_id}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setEditingAssistant(assistant)}
                      aria-label="Редактировать"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(assistant.id)}
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
          icon={Bot}
          title="Нет ассистентов"
          description="Создайте первого AI-ассистента"
          action={{
            label: 'Добавить ассистента',
            onClick: () => setIsCreateOpen(true),
          }}
        />
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editingAssistant} onOpenChange={() => setEditingAssistant(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Редактировать ассистента</DialogTitle>
            <DialogDescription>
              Измените параметры ассистента
            </DialogDescription>
          </DialogHeader>
          {editingAssistant && (
            <AssistantForm
              assistant={editingAssistant}
              modules={modules.filter((m) => m.deleted_at === null)}
              onSubmit={handleUpdate}
              onCancel={() => setEditingAssistant(null)}
              isLoading={updateAssistant.isPending}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

