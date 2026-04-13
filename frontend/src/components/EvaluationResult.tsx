import { CheckCircle2, XCircle, AlertTriangle, Award, TrendingUp, RotateCcw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { Progress } from '@/shared/ui/progress';
import { Markdown } from '@/shared/ui/markdown';
import { cn } from '@/shared/lib/utils';
import type { EvaluateTaskResponse } from '@/api/types';

interface EvaluationResultProps {
  result: EvaluateTaskResponse;
  achievementBadge?: string | null;
  onRetry?: () => void;
}

export function EvaluationResult({ result, achievementBadge, onRetry }: EvaluationResultProps) {
  const isSuccess = result.success;
  const isPassing = result.percentage >= 70;

  return (
    <div className="space-y-4 animate-in slide-in-from-bottom-4">
      {/* Main result card */}
      <Card
        className={cn(
          'border-2',
          isSuccess
            ? 'border-green-500/50 bg-green-500/5'
            : isPassing
            ? 'border-yellow-500/50 bg-yellow-500/5'
            : 'border-red-500/50 bg-red-500/5'
        )}
      >
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isSuccess ? (
                <div className="h-12 w-12 rounded-full bg-green-500/20 flex items-center justify-center">
                  <CheckCircle2 className="h-6 w-6 text-green-500" />
                </div>
              ) : isPassing ? (
                <div className="h-12 w-12 rounded-full bg-yellow-500/20 flex items-center justify-center">
                  <AlertTriangle className="h-6 w-6 text-yellow-500" />
                </div>
              ) : (
                <div className="h-12 w-12 rounded-full bg-red-500/20 flex items-center justify-center">
                  <XCircle className="h-6 w-6 text-red-500" />
                </div>
              )}
              <div>
                <CardTitle className="text-xl">
                  {isSuccess
                    ? 'Задание выполнено!'
                    : isPassing
                    ? 'Неплохо, но можно лучше'
                    : 'Попробуйте еще раз'}
                </CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  {result.stage && `Этап: ${result.stage}`}
                </p>
              </div>
            </div>

            {/* Score badge */}
            <div className="text-right">
              <div className="text-3xl font-bold">
                {result.score}
                <span className="text-lg text-muted-foreground">/{result.max_score}</span>
              </div>
              <Badge
                variant={isSuccess ? 'success' : isPassing ? 'warning' : 'destructive'}
                className="mt-1"
              >
                {result.percentage}%
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Progress bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Прогресс</span>
              <span className="font-medium">{result.percentage}%</span>
            </div>
            <Progress
              value={result.percentage}
              className={cn(
                'h-3',
                isSuccess
                  ? '[&>div]:bg-green-500'
                  : isPassing
                  ? '[&>div]:bg-yellow-500'
                  : '[&>div]:bg-red-500'
              )}
            />
          </div>

          {/* Achievement badge if earned */}
          {isSuccess && achievementBadge && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20">
              <Award className="h-8 w-8 text-amber-500" />
              <div>
                <p className="text-sm font-medium">Получена награда!</p>
                <p className="text-lg">{achievementBadge}</p>
              </div>
            </div>
          )}

          {/* Feedback */}
          <div className="p-4 rounded-lg bg-muted/50 border border-border/50">
            <h4 className="font-medium mb-2 flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary" />
              Обратная связь
            </h4>
            <Markdown content={result.feedback} className="text-sm text-muted-foreground" />
          </div>

          {/* Retry button for non-successful attempts */}
          {!isSuccess && onRetry && (
            <div className="flex justify-center pt-2">
              <Button onClick={onRetry} variant="outline" className="gap-2">
                <RotateCcw className="h-4 w-4" />
                Попробовать ещё раз
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Criteria breakdown */}
      {result.criteria.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Оценка по критериям</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {result.criteria.map((criterion, index) => (
              <div key={index} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>{criterion.name}</span>
                  <span className="font-medium">
                    {criterion.score}/{criterion.max_score}
                  </span>
                </div>
                <Progress
                  value={(criterion.score / criterion.max_score) * 100}
                  className="h-2"
                />
                {criterion.feedback && (
                  <p className="text-xs text-muted-foreground">{criterion.feedback}</p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      {result.recommendations.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Рекомендации</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {result.recommendations.map((rec, index) => (
                <li key={index} className="flex items-start gap-2 text-sm">
                  <span className="text-primary mt-1">•</span>
                  <span className="text-muted-foreground">{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

