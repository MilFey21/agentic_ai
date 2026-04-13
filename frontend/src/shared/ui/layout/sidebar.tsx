import { NavLink } from 'react-router-dom';
import {
  BookOpen,
  BarChart3,
  Layers,
  ListTodo,
  Bot,
} from 'lucide-react';
import { cn } from '@/shared/lib/utils';
import { useIsAdmin } from '@/features';

interface SidebarProps {
  className?: string;
}

interface NavItem {
  title: string;
  href: string;
  icon: React.ElementType;
  adminOnly?: boolean;
}

const mainNav: NavItem[] = [
  { title: 'Модули', href: '/modules', icon: BookOpen },
  { title: 'Мой прогресс', href: '/progress', icon: BarChart3 },
];

const adminNav: NavItem[] = [
  { title: 'Модули', href: '/admin/modules', icon: Layers, adminOnly: true },
  { title: 'Задания', href: '/admin/tasks', icon: ListTodo, adminOnly: true },
  { title: 'Ассистенты', href: '/admin/assistants', icon: Bot, adminOnly: true },
];

export function Sidebar({ className }: SidebarProps) {
  const isAdmin = useIsAdmin();

  return (
    <aside
      className={cn(
        'fixed left-0 top-16 z-40 h-[calc(100vh-4rem)] w-64 border-r border-border/50 bg-background/95 backdrop-blur',
        className
      )}
    >
      <div className="flex h-full flex-col gap-4 p-4">
        <nav className="flex-1 space-y-1">
          <div className="mb-4">
            <h4 className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Обучение
            </h4>
            {mainNav.map((item) => (
              <NavLink
                key={item.href}
                to={item.href}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all hover:bg-accent/10',
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:text-foreground'
                  )
                }
              >
                <item.icon className="h-4 w-4" />
                {item.title}
              </NavLink>
            ))}
          </div>

          {isAdmin && (
            <div>
              <h4 className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Администрирование
              </h4>
              {adminNav.map((item) => (
                <NavLink
                  key={item.href}
                  to={item.href}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all hover:bg-accent/10',
                      isActive
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:text-foreground'
                    )
                  }
                >
                  <item.icon className="h-4 w-4" />
                  {item.title}
                </NavLink>
              ))}
            </div>
          )}
        </nav>

      </div>
    </aside>
  );
}

