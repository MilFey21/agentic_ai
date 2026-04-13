import { useState, useRef, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Bot,
  User,
  Send,
  X,
  Info,
} from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Textarea } from '@/shared/ui/textarea';
import { Avatar, AvatarFallback } from '@/shared/ui/avatar';
import { Badge } from '@/shared/ui/badge';
import { LoadingScreen, Spinner } from '@/shared/ui/spinner';
import { ErrorState } from '@/shared/ui/error-state';
import {
  useModule,
  useAssistants,
  useCreateOrGetSession,
  useEndSession,
  useMessages,
  useSendMessage,
  useChatSessions,
} from '@/features';
import { SENDER_TYPE } from '@/shared/constants';
import { cn } from '@/shared/lib/utils';
import { formatDate } from '@/shared/lib/utils';
import { sanitizeHTML } from '@/shared/lib/sanitize';
import type { Message } from '@/api/types';

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.sender_type === SENDER_TYPE.USER;
  const isSystem = message.sender_type === SENDER_TYPE.SYSTEM;

  if (isSystem) {
    return (
      <div className="flex justify-center my-4">
        <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-muted/50 text-sm text-muted-foreground">
          <Info className="h-4 w-4" />
          <span>{message.content}</span>
        </div>
      </div>
    );
  }

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
            isUser ? 'bg-primary/20 text-primary' : 'bg-secondary/20 text-secondary'
          )}
        >
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>
      <div
        className={cn(
          'max-w-[70%] rounded-lg p-3',
          isUser
            ? 'bg-primary text-primary-foreground rounded-tr-sm'
            : 'bg-muted rounded-tl-sm'
        )}
      >
        <div
          className="text-sm whitespace-pre-wrap break-words"
          dangerouslySetInnerHTML={{ __html: sanitizeHTML(message.content) }}
        />
        <p
          className={cn(
            'text-xs mt-1',
            isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
          )}
        >
          {formatDate(message.created_at)}
        </p>
      </div>
    </div>
  );
}

export function ChatPage() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const navigate = useNavigate();

  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: module, isLoading: moduleLoading } = useModule(moduleId!);
  const { data: assistants = [] } = useAssistants(moduleId!);
  const { data: sessions = [] } = useChatSessions(moduleId);
  
  const activeSession = sessions.find((s) => s.ended_at === null);
  
  const createSession = useCreateOrGetSession();
  const endSession = useEndSession();
  const { data: messages = [], isLoading: messagesLoading } = useMessages(
    activeSession?.id || ''
  );
  const sendMessage = useSendMessage();

  const assistant = assistants[0];

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Create session on mount if not exists
  useEffect(() => {
    if (module && !activeSession && !createSession.isPending) {
      createSession.mutate({
        module_id: module.id,
        flow_id: module.flow_id || undefined,
      });
    }
  }, [module, activeSession]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !activeSession) return;

    const content = inputValue.trim();
    setInputValue('');

    await sendMessage.mutateAsync({
      chat_session_id: activeSession.id,
      sender_type: 'user',
      content,
    });
  };

  const handleEndSession = async () => {
    if (!activeSession) return;
    await endSession.mutateAsync(activeSession.id);
    navigate(`/modules/${moduleId}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
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
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border/50">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link to={`/modules/${moduleId}`} aria-label="Назад к модулю">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div className="flex items-center gap-3">
            <Avatar>
              <AvatarFallback className="bg-secondary/20 text-secondary">
                <Bot className="h-5 w-5" />
              </AvatarFallback>
            </Avatar>
            <div>
              <h1 className="font-semibold">
                {assistant?.name || 'AI-ассистент'}
              </h1>
              <p className="text-xs text-muted-foreground">
                {module.title}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {activeSession && (
            <Badge variant="outline" className="text-xs">
              Сессия активна
            </Badge>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleEndSession}
            disabled={!activeSession || endSession.isPending}
          >
            <X className="h-4 w-4 mr-1" />
            Завершить
          </Button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {messagesLoading ? (
          <div className="flex justify-center py-8">
            <Spinner size="lg" />
          </div>
        ) : messages.length > 0 ? (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {sendMessage.isPending && (
              <div className="flex gap-3">
                <Avatar className="h-8 w-8 shrink-0">
                  <AvatarFallback className="bg-secondary/20 text-secondary">
                    <Bot className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
                <div className="bg-muted rounded-lg rounded-tl-sm p-3">
                  <div className="flex items-center gap-2">
                    <Spinner size="sm" />
                    <span className="text-sm text-muted-foreground">
                      Ассистент думает...
                    </span>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-secondary/10 mb-4">
              <Bot className="h-8 w-8 text-secondary" />
            </div>
            <h3 className="font-semibold text-lg">
              Добро пожаловать в чат!
            </h3>
            <p className="text-muted-foreground mt-2 max-w-md">
              Задавайте вопросы по модулю "{module.title}".
              Ассистент поможет разобраться в материале.
            </p>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="pt-4 border-t border-border/50">
        <div className="flex gap-2">
          <Textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Введите сообщение..."
            className="min-h-[60px] max-h-[120px] resize-none"
            disabled={!activeSession || sendMessage.isPending}
            aria-label="Сообщение"
          />
          <Button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || !activeSession || sendMessage.isPending}
            className="self-end"
            aria-label="Отправить"
          >
            {sendMessage.isPending ? (
              <Spinner size="sm" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          Нажмите Enter для отправки, Shift+Enter для новой строки
        </p>
      </div>
    </div>
  );
}

