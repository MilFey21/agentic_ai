import { useState, useRef, useEffect } from 'react';
import { Send, User, Loader2, AlertCircle, Wind, CheckCircle2 } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/shared/ui/card';
import { Avatar, AvatarFallback } from '@/shared/ui/avatar';
import { Badge } from '@/shared/ui/badge';
import { cn } from '@/shared/lib/utils';
import {
  useCreateAttackSession,
  useSendAttackMessage,
  useActiveAttackSession,
  useAttackMessages,
  useEvaluateAttackSession,
} from '@/features';
import type { Task, AttackChatMessage, EvaluateTaskResponse } from '@/api/types';

interface LangflowChatProps {
  task: Task;
  onSessionCreated?: (sessionId: string) => void;
  onEvaluationComplete?: (result: EvaluateTaskResponse) => void;
}

function MessageBubble({ message }: { message: AttackChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex gap-3 animate-fade-in',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback
          className={cn(
            isUser ? 'bg-primary/20 text-primary' : 'bg-cyan-500/20 text-cyan-400'
          )}
        >
          {isUser ? <User className="h-4 w-4" /> : <Wind className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>
      <div
        className={cn(
          'max-w-[80%] rounded-lg p-3 selectable-text',
          isUser
            ? 'bg-primary text-primary-foreground rounded-tr-sm'
            : 'bg-gradient-to-br from-cyan-950/80 to-teal-950/80 border border-cyan-500/20 rounded-tl-sm'
        )}
      >
        <div className="text-sm whitespace-pre-wrap break-words">
          {message.content}
        </div>
        <p
          className={cn(
            'text-xs mt-1',
            isUser ? 'text-primary-foreground/70' : 'text-cyan-400/50'
          )}
        >
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}

export function LangflowChat({ task, onSessionCreated, onEvaluationComplete }: LangflowChatProps) {
  const [inputValue, setInputValue] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [serviceUnavailable, setServiceUnavailable] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeSession = useActiveAttackSession(task.id);
  const { data: messages = [] } = useAttackMessages(activeSession?.id ?? '');

  const createSession = useCreateAttackSession();
  const sendMessage = useSendAttackMessage();
  const evaluateSession = useEvaluateAttackSession();

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Create session on mount if not exists
  useEffect(() => {
    if (!activeSession && !createSession.isPending && !createSession.isSuccess) {
      createSession.mutate(
        { task_id: task.id },
        {
          onSuccess: (session) => {
            onSessionCreated?.(session.id);
          },
          onError: (err) => {
            const msg = err instanceof Error ? err.message : 'Ошибка при создании сессии';
            if (msg.toLowerCase().includes('langflow') || msg.toLowerCase().includes('credentials') || msg.toLowerCase().includes('provision')) {
              setServiceUnavailable(true);
            } else {
              setError(msg);
            }
          },
        }
      );
    }
  }, [activeSession, task.id]);

  // Notify parent when existing active session is loaded
  useEffect(() => {
    if (activeSession?.id) {
      onSessionCreated?.(activeSession.id);
    }
  }, [activeSession?.id, onSessionCreated]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !activeSession) return;

    const content = inputValue.trim();
    setInputValue('');
    setError(null);

    sendMessage.mutate(
      { sessionId: activeSession.id, content },
      {
        onError: (err) => {
          setError(err instanceof Error ? err.message : 'Ошибка при отправке сообщения');
        },
      }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleEvaluate = () => {
    if (!activeSession) return;

    setError(null);
    evaluateSession.mutate(activeSession.id, {
      onSuccess: (result) => {
        onEvaluationComplete?.(result);
      },
      onError: (err) => {
        setError(err instanceof Error ? err.message : 'Ошибка при оценке диалога');
      },
    });
  };

  const isLoading = createSession.isPending;
  const isSending = sendMessage.isPending;
  const isEvaluating = evaluateSession.isPending;

  return (
    <Card className="border-cyan-500/30 bg-gradient-to-br from-slate-950 to-cyan-950/30">
      <CardHeader className="pb-3 border-b border-cyan-500/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Avatar className="h-10 w-10">
              <AvatarFallback className="bg-cyan-500/20 text-cyan-400">
                <Wind className="h-5 w-5" />
              </AvatarFallback>
            </Avatar>
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                WindChaser Bot
                <Badge variant="outline" className="text-xs border-cyan-500/30 text-cyan-400">
                  LangFlow
                </Badge>
              </CardTitle>
              <CardDescription className="text-cyan-400/60">
                Чат-бот кайтсёрфинг клуба
              </CardDescription>
            </div>
          </div>
          {activeSession && (
            <Badge variant="outline" className="text-xs border-green-500/30 text-green-400">
              Сессия активна
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {/* Messages area */}
        <div className="h-[400px] overflow-y-auto p-4 space-y-4">
          {serviceUnavailable ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-destructive/20 border border-destructive/30 mb-4">
                <AlertCircle className="h-7 w-7 text-destructive" />
              </div>
              <p className="font-medium text-foreground">Сервис временно недоступен</p>
              <p className="text-sm text-muted-foreground mt-2 max-w-xs">
                Чат-бот не может быть запущен. Попробуйте позже или обратитесь к администратору.
              </p>
            </div>
          ) : isLoading ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <Loader2 className="h-8 w-8 text-cyan-400 animate-spin mb-4" />
              <p className="text-muted-foreground">Создаём сессию с ботом...</p>
              <p className="text-xs text-muted-foreground/60 mt-1">
                Это может занять несколько секунд
              </p>
            </div>
          ) : messages.length > 0 ? (
            <>
              {messages.map((message, index) => (
                <MessageBubble key={index} message={message} />
              ))}
              {isSending && (
                <div className="flex gap-3">
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback className="bg-cyan-500/20 text-cyan-400">
                      <Wind className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="bg-gradient-to-br from-cyan-950/80 to-teal-950/80 border border-cyan-500/20 rounded-lg rounded-tl-sm p-3">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 text-cyan-400 animate-spin" />
                      <span className="text-sm text-cyan-400/70">
                        WindChaser Bot думает...
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="relative mb-6">
                <div className="absolute inset-0 bg-cyan-500/20 blur-xl rounded-full"></div>
                <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500/30 to-teal-500/30 border border-cyan-500/30">
                  <Wind className="h-8 w-8 text-cyan-400" />
                </div>
              </div>
              <h3 className="font-semibold text-lg text-cyan-100">
                Добро пожаловать в WindChaser!
              </h3>
              <p className="text-muted-foreground mt-2 max-w-md text-sm">
                Это чат-бот кайтсёрфинг клуба. Попробуйте извлечь из него
                системный промпт с помощью техник промпт-инъекций.
              </p>
              <div className="mt-4 p-3 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-xs text-cyan-400/80">
                💡 Совет: Начните с простых вопросов, чтобы понять поведение бота
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Error message */}
        {error && (
          <div className="px-4 pb-2">
            <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-lg">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          </div>
        )}

        {/* Input area */}
        <div className="p-4 border-t border-cyan-500/20 bg-slate-950/50">
          <div className="flex gap-2">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={serviceUnavailable ? 'Сервис недоступен' : 'Введите ваш промпт для атаки на бота...'}
              className={cn(
                'flex-1 min-h-[60px] max-h-[120px] resize-none rounded-lg border bg-background/50 px-4 py-3 text-sm',
                'focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50',
                'placeholder:text-muted-foreground/50 border-cyan-500/20'
              )}
              disabled={serviceUnavailable || !activeSession || isSending || isEvaluating}
            />
            <Button
              onClick={handleSendMessage}
              disabled={serviceUnavailable || !inputValue.trim() || !activeSession || isSending || isEvaluating}
              className="self-end bg-cyan-600 hover:bg-cyan-500"
            >
              {isSending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          <div className="flex items-center justify-between mt-3">
            <p className="text-xs text-muted-foreground">
              Нажмите Enter для отправки, Shift+Enter для новой строки
            </p>
            <Button
              onClick={handleEvaluate}
              disabled={serviceUnavailable || !activeSession || messages.length === 0 || isSending || isEvaluating}
              variant="default"
              className="bg-emerald-600 hover:bg-emerald-500"
            >
              {isEvaluating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Оценка...
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Отправить на проверку
                </>
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

