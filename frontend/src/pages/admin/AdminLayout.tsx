import { NavLink, Outlet, Navigate } from 'react-router-dom';
import { Settings, Layers, ListTodo, Bot } from 'lucide-react';
import { useIsAdmin } from '@/features';
import { cn } from '@/shared/lib/utils';

const adminNav = [
  { title: 'Модули', href: '/admin/modules', icon: Layers },
  { title: 'Задания', href: '/admin/tasks', icon: ListTodo },
  { title: 'Ассистенты', href: '/admin/assistants', icon: Bot },
];

export function AdminLayout() {
  const isAdmin = useIsAdmin();

  if (!isAdmin) {
    return <Navigate to="/modules" replace />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Settings className="h-8 w-8" />
          Панель администратора
        </h1>
        <p className="text-muted-foreground mt-2">
          Управление контентом платформы
        </p>
      </div>

      <div className="flex gap-2 border-b border-border/50 pb-2">
        {adminNav.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.title}
          </NavLink>
        ))}
      </div>

      <Outlet />
    </div>
  );
}

