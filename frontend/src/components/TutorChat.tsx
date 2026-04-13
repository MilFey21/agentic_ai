import { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Bot, User, Loader2 } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Markdown } from '@/shared/ui/markdown';
import { cn } from '@/shared/lib/utils';
import { chatWithTutor } from '@/api/agents';
import type { Task } from '@/api/types';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface TutorChatProps {
  task: Task;
  currentSolution?: string;
  attackSessionId?: string;  // ID attack session для получения диалога с ботом
  isOpen: boolean;
  onToggle: () => void;
}

export function TutorChat({ task, currentSolution, attackSessionId, isOpen, onToggle }: TutorChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content: `Привет! Я твой тьютор для задания "${task.title}". Задай мне любой вопрос по заданию, и я помогу тебе разобраться!`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await chatWithTutor({
        task_id: task.id,
        task_type: task.type,
        task_title: task.title,
        task_description: task.description,
        message: userMessage.content,
        current_solution: currentSolution,
        attack_session_id: attackSessionId,  // Передаём для получения диалога из LangFlow
        chat_history: messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Извини, произошла ошибка. Попробуй еще раз позже.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Floating button when closed
  if (!isOpen) {
    return (
      <Button
        onClick={onToggle}
        className="fixed top-1/2 right-0 -translate-y-1/2 h-16 w-12 rounded-l-lg rounded-r-none shadow-lg z-40 bg-primary hover:bg-primary/90 flex flex-col items-center justify-center gap-1"
      >
        <MessageCircle className="h-5 w-5" />
        <span className="text-xs writing-mode-vertical">Тьютор</span>
      </Button>
    );
  }

  // Chat panel when open - full height sidebar from right
  return (
    <div className="fixed top-0 right-0 h-full w-[500px] z-50 animate-in slide-in-from-right duration-300">
      <Card className="h-full flex flex-col shadow-2xl border-l-2 border-primary/20 rounded-none">
        <CardHeader className="flex-shrink-0 flex flex-row items-center justify-between py-4 px-6 bg-gradient-to-r from-primary/10 to-primary/5 border-b">
          <div className="flex items-center gap-3">
            <Bot className="h-6 w-6 text-primary" />
            <div>
              <CardTitle className="text-lg">Тьютор</CardTitle>
              <p className="text-xs text-muted-foreground mt-0.5">Помощь по заданию</p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onToggle} className="h-9 w-9">
            <X className="h-5 w-5" />
          </Button>
        </CardHeader>

        <CardContent className="flex-1 overflow-hidden p-0 flex flex-col">
          {/* Messages area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gradient-to-b from-background to-muted/20">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  'flex gap-3',
                  message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                )}
              >
                <div
                  className={cn(
                    'h-9 w-9 rounded-full flex items-center justify-center flex-shrink-0',
                    message.role === 'user'
                      ? 'bg-primary/20'
                      : 'bg-emerald-500/20'
                  )}
                >
                  {message.role === 'user' ? (
                    <User className="h-5 w-5 text-primary" />
                  ) : (
                    <Bot className="h-5 w-5 text-emerald-500" />
                  )}
                </div>
                <div
                  className={cn(
                    'max-w-[75%] rounded-lg px-4 py-3 selectable-text',
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-card border border-border shadow-sm'
                  )}
                >
                  {message.role === 'assistant' ? (
                    <Markdown content={message.content} className="prose prose-sm max-w-none" />
                  ) : (
                    <p className="text-sm">{message.content}</p>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3">
                <div className="h-9 w-9 rounded-full flex items-center justify-center bg-emerald-500/20">
                  <Bot className="h-5 w-5 text-emerald-500" />
                </div>
                <div className="bg-card border border-border rounded-lg px-4 py-3">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="flex-shrink-0 p-4 border-t bg-card">
            <div className="flex gap-3">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Задай вопрос тьютору..."
                className="flex-1 resize-none rounded-lg border border-border bg-background px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 min-h-[60px] max-h-[120px]"
                rows={2}
                disabled={isLoading}
              />
              <Button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                size="icon"
                className="h-[60px] w-12 flex-shrink-0"
              >
                <Send className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

