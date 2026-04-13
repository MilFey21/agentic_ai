import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart3,
  Trophy,
  Target,
  Clock,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Progress } from '@/shared/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select';
import { LoadingScreen } from '@/shared/ui/spinner';
import { EmptyState } from '@/shared/ui/empty-state';
import { useUserProgress, useActiveModules, useAllTasks } from '@/features';
import { TASK_STATUS, TASK_STATUS_LABELS, TASK_TYPE_LABELS } from '@/shared/constants';
import { formatDate } from '@/shared/lib/utils';
import { cn } from '@/shared/lib/utils';
import type { Task, UserTaskProgress, Module } from '@/api/types';

function StatCard({
  icon: Icon,
  label,
  value,
  color = 'primary',
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color?: 'primary' | 'secondary' | 'success' | 'warning';
}) {
  const colorClasses = {
    primary: 'bg-primary/10 text-primary',
    secondary: 'bg-secondary/10 text-secondary',
    success: 'bg-green-500/10 text-green-400',
    warning: 'bg-yellow-500/10 text-yellow-400',
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-4">
          <div className={cn('flex h-12 w-12 items-center justify-center rounded-lg', colorClasses[color])}>
            <Icon className="h-6 w-6" />
          </div>
          <div>
            <p className="text-3xl font-bold">{value}</p>
            <p className="text-sm text-muted-foreground">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ProgressRow({
  progress,
  task,
  module,
}: {
  progress: UserTaskProgress;
  task: Task | undefined;
  module: Module | undefined;
}) {
  const statusConfig = {
    [TASK_STATUS.NOT_STARTED]: { icon: Clock, color: 'text-muted-foreground', bg: 'bg-muted' },
    [TASK_STATUS.IN_PROGRESS]: { icon: Target, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
    [TASK_STATUS.COMPLETED]: { icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-500/10' },
    [TASK_STATUS.FAILED]: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10' },
  };

  const config = statusConfig[progress.status];
  const StatusIcon = config.icon;

  return (
    <div className="flex items-center gap-4 p-4 rounded-lg border border-border/50 hover:border-primary/30 transition-colors">
      <div className={cn('flex h-10 w-10 items-center justify-center rounded-lg', config.bg)}>
        <StatusIcon className={cn('h-5 w-5', config.color)} />
      </div>

      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{task?.title || 'Неизвестное задание'}</p>
        <div className="flex items-center gap-2 mt-1">
          {module && (
            <Link
              to={`/modules/${module.id}`}
              className="text-xs text-primary hover:underline"
            >
              {module.title}
            </Link>
          )}
          {task && (
            <Badge variant="outline" className="text-xs">
              {TASK_TYPE_LABELS[task.type] || task.type}
            </Badge>
          )}
        </div>
      </div>

      <div className="text-right shrink-0">
        <Badge
          variant={progress.status === TASK_STATUS.COMPLETED ? 'success' : 'outline'}
        >
          {TASK_STATUS_LABELS[progress.status]}
        </Badge>
        {progress.score !== null && (
          <p className="text-sm text-muted-foreground mt-1">
            {progress.score} / {task?.max_score || '?'} баллов
          </p>
        )}
      </div>

      <div className="text-right text-xs text-muted-foreground shrink-0 w-24">
        {progress.completed_at ? (
          <div>
            <p>Завершено</p>
            <p>{formatDate(progress.completed_at)}</p>
          </div>
        ) : progress.started_at ? (
          <div>
            <p>Начато</p>
            <p>{formatDate(progress.started_at)}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function ProgressPage() {
  const [moduleFilter, setModuleFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const { data: progress = [], isLoading: progressLoading } = useUserProgress();
  const { data: modules = [] } = useActiveModules();
  const { data: allTasks = [] } = useAllTasks();

  if (progressLoading) {
    return <LoadingScreen />;
  }

  // Filter progress
  let filteredProgress = progress;

  if (moduleFilter !== 'all') {
    const moduleTasks = allTasks.filter((t) => t.module_id === moduleFilter);
    const moduleTaskIds = moduleTasks.map((t) => t.id);
    filteredProgress = filteredProgress.filter((p) => moduleTaskIds.includes(p.task_id));
  }

  if (statusFilter !== 'all') {
    filteredProgress = filteredProgress.filter((p) => p.status === statusFilter);
  }

  // Calculate stats
  const totalTasks = allTasks.length;
  const completedCount = progress.filter((p) => p.status === TASK_STATUS.COMPLETED).length;
  const inProgressCount = progress.filter((p) => p.status === TASK_STATUS.IN_PROGRESS).length;
  const totalScore = progress.reduce((sum, p) => sum + (p.score || 0), 0);
  const completionRate = totalTasks > 0 ? (completedCount / totalTasks) * 100 : 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Мой прогресс</h1>
        <p className="text-muted-foreground mt-2">
          Отслеживайте свой прогресс в изучении информационной безопасности
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={CheckCircle2}
          label="Заданий выполнено"
          value={completedCount}
          color="success"
        />
        <StatCard
          icon={Target}
          label="В процессе"
          value={inProgressCount}
          color="warning"
        />
        <StatCard
          icon={Trophy}
          label="Всего баллов"
          value={totalScore}
          color="secondary"
        />
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Общий прогресс</span>
                <span className="font-medium">{Math.round(completionRate)}%</span>
              </div>
              <Progress value={completionRate} className="h-2" />
              <p className="text-xs text-muted-foreground">
                {completedCount} из {totalTasks} заданий
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                История заданий
              </CardTitle>
              <CardDescription>
                Все ваши задания и их статусы
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Select value={moduleFilter} onValueChange={setModuleFilter}>
                <SelectTrigger className="w-[180px]" aria-label="Фильтр по модулю">
                  <SelectValue placeholder="Все модули" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все модули</SelectItem>
                  {modules.map((module) => (
                    <SelectItem key={module.id} value={module.id}>
                      {module.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[150px]" aria-label="Фильтр по статусу">
                  <SelectValue placeholder="Все статусы" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все статусы</SelectItem>
                  {Object.entries(TASK_STATUS_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredProgress.length > 0 ? (
            <div className="space-y-3">
              {filteredProgress.map((p) => {
                const task = allTasks.find((t) => t.id === p.task_id);
                const module = modules.find((m) => m.id === task?.module_id);
                return (
                  <ProgressRow
                    key={p.id}
                    progress={p}
                    task={task}
                    module={module}
                  />
                );
              })}
            </div>
          ) : (
            <EmptyState
              icon={BarChart3}
              title="Нет данных"
              description={
                progress.length === 0
                  ? 'Вы ещё не начинали выполнять задания'
                  : 'Нет заданий, соответствующих фильтрам'
              }
              action={
                progress.length === 0
                  ? {
                      label: 'Начать обучение',
                      onClick: () => {},
                    }
                  : undefined
              }
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

