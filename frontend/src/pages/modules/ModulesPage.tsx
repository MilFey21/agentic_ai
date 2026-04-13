import { Link } from 'react-router-dom';
import { BookOpen, ChevronRight, Sparkles } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card';
import { Progress } from '@/shared/ui/progress';
import { Badge } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';
import { LoadingScreen } from '@/shared/ui/spinner';
import { EmptyState } from '@/shared/ui/empty-state';
import { ErrorState } from '@/shared/ui/error-state';
import { useActiveModules, useUserProgress } from '@/features';
import type { Module, Task, UserTaskProgress } from '@/api/types';

function ModuleCard({
  module,
  tasks,
  progress,
}: {
  module: Module;
  tasks: Task[];
  progress: UserTaskProgress[];
}) {
  const moduleTasks = tasks.filter((t) => t.module_id === module.id);
  const completedTasks = progress.filter(
    (p) =>
      p.status === 'completed' &&
      moduleTasks.some((t) => t.id === p.task_id)
  ).length;
  const totalTasks = moduleTasks.length;
  const progressPercent = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;

  return (
    <Link to={`/modules/${module.id}`} className="group">
      <Card className="h-full transition-all hover:border-primary/50 hover:shadow-[0_0_20px_hsl(var(--primary)/0.1)]">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <BookOpen className="h-6 w-6" />
            </div>
            {progressPercent === 100 && (
              <Badge variant="success" className="flex items-center gap-1">
                <Sparkles className="h-3 w-3" />
                Завершён
              </Badge>
            )}
          </div>
          <CardTitle className="mt-4 line-clamp-2 group-hover:text-primary transition-colors">
            {module.title}
          </CardTitle>
          <CardDescription className="line-clamp-2">
            {module.description}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Прогресс</span>
              <span className="font-medium">
                {completedTasks} / {totalTasks} заданий
              </span>
            </div>
            <Progress value={progressPercent} className="h-2" />
          </div>
          <div className="mt-4 flex items-center justify-end">
            <Button variant="ghost" size="sm" className="group-hover:text-primary">
              Открыть
              <ChevronRight className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export function ModulesPage() {
  const { data: modules, isLoading, error, refetch } = useActiveModules();
  const { data: allProgress = [] } = useUserProgress();

  // Fetch all tasks for progress calculation
  const allTasks: Task[] = [];
  
  if (isLoading) {
    return <LoadingScreen />;
  }

  if (error) {
    return (
      <ErrorState
        message="Не удалось загрузить модули"
        onRetry={() => refetch()}
      />
    );
  }

  if (!modules || modules.length === 0) {
    return (
      <EmptyState
        icon={BookOpen}
        title="Модули не найдены"
        description="Пока нет доступных модулей для изучения"
      />
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Каталог модулей</h1>
        <p className="text-muted-foreground mt-2">
          Выберите модуль для изучения информационной безопасности
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 stagger-fade-in">
        {modules.map((module) => (
          <ModuleCard
            key={module.id}
            module={module}
            tasks={allTasks}
            progress={allProgress}
          />
        ))}
      </div>
    </div>
  );
}

