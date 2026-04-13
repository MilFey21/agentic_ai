import { Link, useNavigate } from 'react-router-dom';
import { Shield, LogOut, Settings, BookOpen, BarChart3 } from 'lucide-react';
import { Button } from '../button';
import { Avatar, AvatarFallback } from '../avatar';
import { useCurrentUser, useIsAdmin, useLogout } from '@/features';
import { cn } from '@/shared/lib/utils';

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  const user = useCurrentUser();
  const isAdmin = useIsAdmin();
  const logout = useLogout();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getInitials = (name: string) => {
    return name
      .split(/[_\s]/)
      .map((part) => part[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <header
      className={cn(
        'sticky top-0 z-50 w-full border-b border-border/50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60',
        className
      )}
    >
      <div className="flex h-16 w-full items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-6">
          <Link to="/modules" className="flex items-center gap-2 group">
            <div className="relative">
              <Shield className="h-8 w-8 text-primary transition-transform group-hover:scale-110" />
              <div className="absolute inset-0 blur-lg bg-primary/30 group-hover:bg-primary/50 transition-colors" />
            </div>
            <span className="font-display text-xl font-bold tracking-wider text-foreground">
              WIND<span className="text-primary">CHASER</span>
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            <Button variant="ghost" asChild>
              <Link to="/modules" className="flex items-center gap-2">
                <BookOpen className="h-4 w-4" />
                Модули
              </Link>
            </Button>
            <Button variant="ghost" asChild>
              <Link to="/progress" className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                Прогресс
              </Link>
            </Button>
            {isAdmin && (
              <Button variant="ghost" asChild>
                <Link to="/admin" className="flex items-center gap-2">
                  <Settings className="h-4 w-4" />
                  Админ
                </Link>
              </Button>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-4">
          {user && (
            <div className="flex items-center gap-3">
              <div className="hidden sm:block text-right">
                <p className="text-sm font-medium">{user.username}</p>
                <p className="text-xs text-muted-foreground capitalize">
                  {user.role?.name}
                </p>
              </div>
              <Avatar>
                <AvatarFallback className="bg-primary/20 text-primary">
                  {getInitials(user.username)}
                </AvatarFallback>
              </Avatar>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                aria-label="Выйти"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

