import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Play,
  MessageSquare,
  Target,
  Bot,
  CheckCircle2,
  Clock,
  Trophy,
} from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Progress } from '@/shared/ui/progress';
import { LoadingScreen } from '@/shared/ui/spinner';
import { ErrorState } from '@/shared/ui/error-state';
import {
  useModule,
  useMissions,
  useTasks,
  useAssistants,
  useUserProgress,
} from '@/features';
import { TASK_STATUS, TASK_STATUS_LABELS, TASK_TYPE_LABELS } from '@/shared/constants';
import { cn } from '@/shared/lib/utils';
import type { Task, UserTaskProgress } from '@/api/types';

function TaskCard({
  task,
  progress,
}: {
  task: Task;
  progress: UserTaskProgress | undefined;
}) {
  const status = progress?.status || TASK_STATUS.NOT_STARTED;
  const statusColors = {
    [TASK_STATUS.NOT_STARTED]: 'text-muted-foreground',
    [TASK_STATUS.IN_PROGRESS]: 'text-yellow-400',
    [TASK_STATUS.COMPLETED]: 'text-green-400',
    [TASK_STATUS.FAILED]: 'text-red-400',
  };

  const statusIcons = {
    [TASK_STATUS.NOT_STARTED]: Clock,
    [TASK_STATUS.IN_PROGRESS]: Play,
    [TASK_STATUS.COMPLETED]: CheckCircle2,
    [TASK_STATUS.FAILED]: Target,
  };

  const StatusIcon = statusIcons[status];

  return (
    <div
      className={cn(
        'flex items-center gap-4 p-4 rounded-lg border border-border/50 transition-all hover:border-primary/30',
        status === TASK_STATUS.COMPLETED && 'bg-green-500/5 border-green-500/20'
      )}
    >
      <div
        className={cn(
          'flex h-10 w-10 items-center justify-center rounded-lg',
          status === TASK_STATUS.COMPLETED
            ? 'bg-green-500/20'
            : 'bg-muted'
        )}
      >
        <StatusIcon className={cn('h-5 w-5', statusColors[status])} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className="font-medium truncate">{task.title}</h4>
          {task.achievement_badge && status === TASK_STATUS.COMPLETED && (
            <span className="text-lg">{task.achievement_badge}</span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-1">
          <Badge variant="outline" className="text-xs">
            {TASK_TYPE_LABELS[task.type] || task.type}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {task.max_score} баллов
          </span>
          {progress?.score && (
            <span className="text-xs text-green-400">
              Набрано: {progress.score}
            </span>
          )}
        </div>
      </div>
      <Badge
        variant={status === TASK_STATUS.COMPLETED ? 'success' : 'outline'}
        className="shrink-0"
      >
        {TASK_STATUS_LABELS[status]}
      </Badge>
    </div>
  );
}

export function ModuleDetailPage() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const navigate = useNavigate();

  const { data: module, isLoading: moduleLoading, error: moduleError } = useModule(moduleId!);
  const { data: missions = [] } = useMissions(moduleId!);
  const { data: tasks = [] } = useTasks(moduleId!);
  const { data: assistants = [] } = useAssistants(moduleId!);
  const { data: progress = [] } = useUserProgress(moduleId);

  if (moduleLoading) {
    return <LoadingScreen />;
  }

  if (moduleError || !module) {
    return (
      <ErrorState
        message="Модуль не найден"
        onRetry={() => navigate('/modules')}
      />
    );
  }

  const completedTasks = progress.filter((p) => p.status === TASK_STATUS.COMPLETED).length;
  const progressPercent = tasks.length > 0 ? (completedTasks / tasks.length) * 100 : 0;
  const totalScore = progress.reduce((sum, p) => sum + (p.score || 0), 0);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/modules" aria-label="Назад к модулям">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold tracking-tight">{module.title}</h1>
          <p className="text-muted-foreground mt-2">{module.description}</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Target className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {completedTasks}/{tasks.length}
                </p>
                <p className="text-xs text-muted-foreground">Заданий выполнено</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary/10">
                <Trophy className="h-5 w-5 text-secondary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{totalScore}</p>
                <p className="text-xs text-muted-foreground">Баллов набрано</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Прогресс модуля</span>
                <span className="font-medium">{Math.round(progressPercent)}%</span>
              </div>
              <Progress value={progressPercent} className="h-2" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Actions */}
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link to={`/modules/${moduleId}/player`}>
                <Play className="mr-2 h-4 w-4" />
                {progressPercent > 0 ? 'Продолжить обучение' : 'Начать обучение'}
              </Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link to={`/chat/${moduleId}`}>
                <MessageSquare className="mr-2 h-4 w-4" />
                Чат с ассистентом
              </Link>
            </Button>
          </div>

          {/* Missions */}
          {missions.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Миссии</CardTitle>
                <CardDescription>
                  Выполняйте миссии для изучения материала
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {missions.map((mission) => (
                    <div
                      key={mission.id}
                      className="flex items-center gap-3 p-3 rounded-lg bg-muted/50"
                    >
                      <Badge variant="outline" className="font-mono">
                        {mission.code}
                      </Badge>
                      <div className="flex-1">
                        <p className="font-medium">{mission.title}</p>
                        <p className="text-sm text-muted-foreground line-clamp-1">
                          {mission.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Tasks */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Задания</CardTitle>
              <CardDescription>
                Выполните все задания для завершения модуля
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {tasks.map((task) => {
                  const taskProgress = progress.find((p) => p.task_id === task.id);
                  return (
                    <TaskCard key={task.id} task={task} progress={taskProgress} />
                  );
                })}
                {tasks.length === 0 && (
                  <p className="text-center text-muted-foreground py-8">
                    В этом модуле пока нет заданий
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Assistants */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Bot className="h-5 w-5" />
                AI-ассистенты
              </CardTitle>
              <CardDescription>
                Помощники для изучения модуля
              </CardDescription>
            </CardHeader>
            <CardContent>
              {assistants.length > 0 ? (
                <div className="space-y-3">
                  {assistants.map((assistant) => (
                    <div
                      key={assistant.id}
                      className="p-3 rounded-lg border border-border/50 hover:border-primary/30 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20">
                          <Bot className="h-4 w-4 text-primary" />
                        </div>
                        <span className="font-medium">{assistant.name}</span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                        {assistant.system_prompt}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  Нет доступных ассистентов
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

