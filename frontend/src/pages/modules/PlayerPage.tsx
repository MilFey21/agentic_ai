import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  BookOpen,
  Code,
  HelpCircle,
  CheckCircle2,
  Play,
  Award,
  Target,
} from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs';
import { LoadingScreen, Spinner } from '@/shared/ui/spinner';
import { ErrorState } from '@/shared/ui/error-state';
import { EmptyState } from '@/shared/ui/empty-state';
import { Markdown } from '@/shared/ui/markdown';
import { TutorChat, EvaluationResult, LangflowChat } from '@/components';
import {
  useModule,
  useLessons,
  useTasks,
  useUserProgress,
  useCreateProgress,
  useUpdateProgress,
  useCurrentUser,
} from '@/features';
import { TASK_STATUS, TASK_TYPE_LABELS, LESSON_TYPE_LABELS, ATTACK_TASK_TYPES } from '@/shared/constants';
import { cn } from '@/shared/lib/utils';
import type { Task, Lesson, UserTaskProgress, EvaluateTaskResponse } from '@/api/types';

// Task type renderers (stateless, description only)
const TaskDescriptionRenderers: Record<string, React.FC<{ task: Task }>> = {
  theory: ({ task }) => (
    <div className="space-y-4">
      <Markdown content={task.description} />
      <div className="mt-6 p-4 rounded-lg bg-muted/50 border border-border/50">
        <p className="text-sm">
          📚 Это теоретический материал. Изучите информацию выше и нажмите
          "Отметить как изученное" для продолжения.
        </p>
      </div>
    </div>
  ),
  practice: ({ task }) => (
    <div className="space-y-4">
      <Markdown content={task.description} />
      <div className="p-4 rounded-lg bg-muted/50 border border-border/50 font-mono text-sm">
        <p className="text-primary"># Практическое задание</p>
        <p className="text-muted-foreground mt-2">
          Выполните задание согласно инструкции выше.
        </p>
        <p className="text-muted-foreground mt-1">
          После выполнения нажмите "Отправить на проверку".
        </p>
      </div>
    </div>
  ),
  quiz: ({ task }) => (
    <div className="space-y-4">
      <Markdown content={task.description} />
      <div className="p-4 rounded-lg bg-primary/10 border border-primary/20">
        <p className="text-sm flex items-center gap-2">
          <HelpCircle className="h-4 w-4 text-primary" />
          Это тестовое задание. Ответьте на вопросы для проверки знаний.
        </p>
      </div>
      <div className="space-y-3 mt-4">
        <p className="font-medium">Вопрос 1: Что такое файрвол?</p>
        <div className="space-y-2">
          {['Система безопасности для контроля трафика', 'Антивирусная программа', 'Операционная система', 'Браузер'].map((option, i) => (
            <label
              key={i}
              className="flex items-center gap-3 p-3 rounded-lg border border-border/50 cursor-pointer hover:border-primary/30 transition-colors"
            >
              <input type="radio" name="q1" className="accent-primary" />
              <span>{option}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  ),
  attack: ({ task }) => (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-primary mb-4">
        <Target className="h-5 w-5" />
        <span className="font-medium">Задание на атаку</span>
      </div>
      <Markdown content={task.description} />
    </div>
  ),
  // Specific attack types use the same renderer
  system_prompt_extraction: ({ task }) => (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-primary mb-4">
        <Target className="h-5 w-5" />
        <span className="font-medium">Извлечение системного промпта</span>
      </div>
      <Markdown content={task.description} />
    </div>
  ),
  knowledge_base_secret_extraction: ({ task }) => (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-primary mb-4">
        <Target className="h-5 w-5" />
        <span className="font-medium">Извлечение секрета из базы знаний</span>
      </div>
      <Markdown content={task.description} />
    </div>
  ),
  token_limit_bypass: ({ task }) => (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-primary mb-4">
        <Target className="h-5 w-5" />
        <span className="font-medium">Обход лимита токенов</span>
      </div>
      <Markdown content={task.description} />
    </div>
  ),
};

// Fallback renderer
const FallbackDescriptionRenderer: React.FC<{ task: Task }> = ({ task }) => (
  <div className="space-y-4">
    <Markdown content={task.description} />
    <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
      <p className="text-sm text-yellow-400">
        ⚠️ Тип задания "{task.type}" не поддерживается в текущей версии.
      </p>
    </div>
  </div>
);

function TaskView({
  task,
  progress,
  onStart,
  onComplete,
  isLoading,
  isStarting,
}: {
  task: Task;
  progress: UserTaskProgress | undefined;
  onStart: () => Promise<void>;
  onComplete: (score?: number) => void;
  isLoading: boolean;
  isStarting?: boolean;
}) {
  const [currentSolution] = useState('');
  const [evaluationResult, setEvaluationResult] = useState<EvaluateTaskResponse | null>(null);
  const [isTutorOpen, setIsTutorOpen] = useState(false);
  const [localStatus, setLocalStatus] = useState<string | null>(null);
  const [attackSessionId, setAttackSessionId] = useState<string | undefined>(undefined);

  const DescriptionRenderer = TaskDescriptionRenderers[task.type] || FallbackDescriptionRenderer;
  // Use local status if set (after starting), otherwise use progress status
  const status = localStatus || progress?.status || TASK_STATUS.NOT_STARTED;
  const isAttackTask = (ATTACK_TASK_TYPES as readonly string[]).includes(task.type);

  // Reset local status when progress updates
  useEffect(() => {
    if (progress?.status) {
      setLocalStatus(null);
    }
  }, [progress?.status]);

  const handleStart = async () => {
    await onStart();
    // Immediately update local status so UI reacts without waiting for refetch
    setLocalStatus(TASK_STATUS.IN_PROGRESS);
  };

  const handleEvaluationComplete = (result: EvaluateTaskResponse) => {
    setEvaluationResult(result);
    if (result.success) {
      onComplete(result.score);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">{task.title}</h2>
          <div className="flex items-center gap-3 mt-2">
            <Badge variant="outline">
              {TASK_TYPE_LABELS[task.type] || task.type}
            </Badge>
            <span className="text-sm text-muted-foreground">
              Максимум {task.max_score} баллов
            </span>
            {task.achievement_badge && (
              <span className="text-sm">
                Награда: {task.achievement_badge}
              </span>
            )}
          </div>
        </div>
        {status === TASK_STATUS.COMPLETED && (
          <div className="flex items-center gap-2 text-green-400">
            <CheckCircle2 className="h-5 w-5" />
            <span className="font-medium">Выполнено</span>
            {progress?.score && (
              <Badge variant="success">{progress.score} баллов</Badge>
            )}
          </div>
        )}
      </div>

      {/* Task description */}
      <Card>
        <CardContent className="pt-6">
          <DescriptionRenderer task={task} />
        </CardContent>
      </Card>

      {/* LangFlow Chat for attack tasks - show when task is in progress */}
      {isAttackTask && status === TASK_STATUS.IN_PROGRESS && (
        <LangflowChat
          task={task}
          onSessionCreated={setAttackSessionId}
          onEvaluationComplete={handleEvaluationComplete}
        />
      )}

      {/* Evaluation result - appears below chat */}
      {evaluationResult && (
        <EvaluationResult
          result={evaluationResult}
          achievementBadge={task.achievement_badge}
          onRetry={() => setEvaluationResult(null)}
        />
      )}

      {/* Action buttons for non-attack tasks */}
      {!isAttackTask && (
        <div className="flex items-center gap-3">
          {status === TASK_STATUS.NOT_STARTED && (
            <Button onClick={handleStart} disabled={isLoading || isStarting}>
              {(isLoading || isStarting) ? <Spinner size="sm" className="mr-2" /> : <Play className="mr-2 h-4 w-4" />}
              Начать задание
            </Button>
          )}
          {status === TASK_STATUS.IN_PROGRESS && (
            <Button onClick={() => onComplete()} disabled={isLoading}>
              {isLoading ? (
                <Spinner size="sm" className="mr-2" />
              ) : (
                <CheckCircle2 className="mr-2 h-4 w-4" />
              )}
              {task.type === 'theory' ? 'Отметить как изученное' : 'Отправить на проверку'}
            </Button>
          )}
          {status === TASK_STATUS.COMPLETED && (
            <div className="flex items-center gap-2 text-green-400">
              <Award className="h-5 w-5" />
              <span>Задание успешно выполнено!</span>
            </div>
          )}
        </div>
      )}

      {/* Attack task buttons */}
      {isAttackTask && (
        <div className="flex items-center gap-3">
          {status === TASK_STATUS.NOT_STARTED && (
            <Button onClick={handleStart} disabled={isLoading || isStarting}>
              {(isLoading || isStarting) ? <Spinner size="sm" className="mr-2" /> : <Play className="mr-2 h-4 w-4" />}
              Начать задание
            </Button>
          )}
          {status === TASK_STATUS.COMPLETED && !evaluationResult && (
            <div className="flex items-center gap-2 text-green-400">
              <Award className="h-5 w-5" />
              <span>Задание успешно выполнено!</span>
            </div>
          )}
        </div>
      )}

      {/* Tutor chat for attack tasks */}
      {isAttackTask && status === TASK_STATUS.IN_PROGRESS && (
        <TutorChat
          task={task}
          currentSolution={currentSolution}
          attackSessionId={attackSessionId}
          isOpen={isTutorOpen}
          onToggle={() => setIsTutorOpen(!isTutorOpen)}
        />
      )}
    </div>
  );
}

function LessonView({ lesson }: { lesson: Lesson }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">{lesson.title}</h2>
        <Badge variant="outline" className="mt-2">
          {LESSON_TYPE_LABELS[lesson.type] || lesson.type}
        </Badge>
      </div>

      <Card>
        <CardContent className="pt-6">
          <p className="text-muted-foreground">
            Контент урока "{lesson.title}" типа "{lesson.type}".
          </p>
          <div className="mt-4 p-4 rounded-lg bg-muted/50">
            <p className="text-sm">
              В реальной системе здесь будет отображаться контент урока,
              загруженный из LangFlow или базы данных.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function PlayerPage() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const navigate = useNavigate();
  const user = useCurrentUser();

  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedLessonId, setSelectedLessonId] = useState<string | null>(null);

  const { data: module, isLoading: moduleLoading } = useModule(moduleId!);
  const { data: lessons = [] } = useLessons(module?.flow_id || '');
  const { data: tasks = [] } = useTasks(moduleId!);
  const { data: progress = [] } = useUserProgress(moduleId);

  const createProgress = useCreateProgress();
  const updateProgress = useUpdateProgress();

  const selectedTask = tasks.find((t) => t.id === selectedTaskId);
  const selectedLesson = lessons.find((l) => l.id === selectedLessonId);
  const taskProgress = progress.find((p) => p.task_id === selectedTaskId);

  const handleStartTask = async () => {
    if (!selectedTaskId || !user) return;

    await createProgress.mutateAsync({
      user_id: user.id,
      task_id: selectedTaskId,
      status: 'in_progress',
      started_at: new Date().toISOString(),
    });
  };

  const handleCompleteTask = async (score?: number) => {
    if (!taskProgress) return;

    // Use provided score or generate random score for demo
    const finalScore = score ?? Math.floor(Math.random() * 30) + 70;

    await updateProgress.mutateAsync({
      id: taskProgress.id,
      data: {
        status: 'completed',
        score: finalScore,
        completed_at: new Date().toISOString(),
      },
    });
  };

  if (moduleLoading) {
    return <LoadingScreen />;
  }

  if (!module) {
    return (
      <ErrorState
        message="Модуль не найден"
        onRetry={() => navigate('/modules')}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to={`/modules/${moduleId}`} aria-label="Назад к модулю">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold">{module.title}</h1>
          <p className="text-sm text-muted-foreground">Плеер обучения</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        {/* Sidebar - Navigation */}
        <div className="lg:col-span-1">
          <Tabs defaultValue="tasks" className="w-full">
            <TabsList className="w-full">
              <TabsTrigger value="lessons" className="flex-1">
                <BookOpen className="h-4 w-4 mr-1" />
                Уроки
              </TabsTrigger>
              <TabsTrigger value="tasks" className="flex-1">
                <Code className="h-4 w-4 mr-1" />
                Задания
              </TabsTrigger>
            </TabsList>

            <TabsContent value="lessons" className="mt-4">
              <div className="space-y-2">
                {lessons.length > 0 ? (
                  lessons.map((lesson) => (
                    <button
                      key={lesson.id}
                      onClick={() => {
                        setSelectedLessonId(lesson.id);
                        setSelectedTaskId(null);
                      }}
                      className={cn(
                        'w-full text-left p-3 rounded-lg border transition-all',
                        selectedLessonId === lesson.id
                          ? 'border-primary bg-primary/10'
                          : 'border-border/50 hover:border-primary/30'
                      )}
                    >
                      <p className="font-medium text-sm truncate">{lesson.title}</p>
                      <Badge variant="outline" className="mt-1 text-xs">
                        {LESSON_TYPE_LABELS[lesson.type] || lesson.type}
                      </Badge>
                    </button>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    Нет уроков
                  </p>
                )}
              </div>
            </TabsContent>

            <TabsContent value="tasks" className="mt-4">
              <div className="space-y-2">
                {tasks.length > 0 ? (
                  tasks.map((task) => {
                    const taskProg = progress.find((p) => p.task_id === task.id);
                    const isCompleted = taskProg?.status === TASK_STATUS.COMPLETED;

                    return (
                      <button
                        key={task.id}
                        onClick={() => {
                          setSelectedTaskId(task.id);
                          setSelectedLessonId(null);
                        }}
                        className={cn(
                          'w-full text-left p-3 rounded-lg border transition-all',
                          selectedTaskId === task.id
                            ? 'border-primary bg-primary/10'
                            : 'border-border/50 hover:border-primary/30',
                          isCompleted && 'border-green-500/30 bg-green-500/5'
                        )}
                      >
                        <div className="flex items-center gap-2">
                          {isCompleted && (
                            <CheckCircle2 className="h-4 w-4 text-green-400 shrink-0" />
                          )}
                          <p className="font-medium text-sm truncate">{task.title}</p>
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="outline" className="text-xs">
                            {TASK_TYPE_LABELS[task.type] || task.type}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {task.max_score} б.
                          </span>
                        </div>
                      </button>
                    );
                  })
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    Нет заданий
                  </p>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Main content */}
        <div className="lg:col-span-3">
          {selectedTask ? (
            <TaskView
              key={selectedTask.id}
              task={selectedTask}
              progress={taskProgress}
              onStart={handleStartTask}
              onComplete={handleCompleteTask}
              isLoading={updateProgress.isPending}
              isStarting={createProgress.isPending}
            />
          ) : selectedLesson ? (
            <LessonView lesson={selectedLesson} />
          ) : (
            <EmptyState
              icon={BookOpen}
              title="Выберите урок или задание"
              description="Выберите элемент из списка слева для начала обучения"
            />
          )}
        </div>
      </div>
    </div>
  );
}

