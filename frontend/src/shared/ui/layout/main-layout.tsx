import { Outlet } from 'react-router-dom';
import { Header } from './header';
import { Sidebar } from './sidebar';
import { cn } from '@/shared/lib/utils';

interface MainLayoutProps {
  className?: string;
  hideSidebar?: boolean;
}

export function MainLayout({ className, hideSidebar }: MainLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="flex">
        {!hideSidebar && <Sidebar />}
        <main
          className={cn(
            'flex-1 p-6',
            !hideSidebar && 'ml-64',
            className
          )}
        >
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

