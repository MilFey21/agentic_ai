import { createBrowserRouter, Navigate } from 'react-router-dom';
import { MainLayout } from '@/shared/ui/layout';
import { LoginPage } from '@/pages/login';
import { ModulesPage, ModuleDetailPage, PlayerPage } from '@/pages/modules';
import { ProgressPage } from '@/pages/progress';
import { ChatPage } from '@/pages/chat';
import {
  AdminLayout,
  AdminModulesPage,
  AdminTasksPage,
  AdminAssistantsPage,
} from '@/pages/admin';
import { ProtectedRoute } from './ProtectedRoute';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/modules" replace />,
      },
      {
        path: 'modules',
        element: <ModulesPage />,
      },
      {
        path: 'modules/:moduleId',
        element: <ModuleDetailPage />,
      },
      {
        path: 'modules/:moduleId/player',
        element: <PlayerPage />,
      },
      {
        path: 'progress',
        element: <ProgressPage />,
      },
      {
        path: 'chat/:moduleId',
        element: <ChatPage />,
      },
      {
        path: 'admin',
        element: <AdminLayout />,
        children: [
          {
            index: true,
            element: <Navigate to="/admin/modules" replace />,
          },
          {
            path: 'modules',
            element: <AdminModulesPage />,
          },
          {
            path: 'tasks',
            element: <AdminTasksPage />,
          },
          {
            path: 'assistants',
            element: <AdminAssistantsPage />,
          },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/modules" replace />,
  },
]);

