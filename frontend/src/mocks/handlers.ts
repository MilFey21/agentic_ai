import { http, HttpResponse, delay } from 'msw';
import { db, auth, dbHelpers } from './data/db';

const API_DELAY = 300;

// Helper to simulate network delay
const withDelay = async <T>(data: T): Promise<T> => {
  await delay(API_DELAY);
  return data;
};

// Assistant response templates
const assistantResponses = [
  'Отличный вопрос! Давайте разберём это подробнее...',
  'Хороший вопрос. В контексте информационной безопасности это означает...',
  'Позвольте объяснить. Это важная тема в ИБ...',
  'Интересно! Вот что я могу рассказать по этой теме...',
];

export const handlers = [
  // Auth endpoints
  http.get('/api/me', async () => {
    const user = auth.getCurrentUser();
    if (!user) {
      return HttpResponse.json({ message: 'Not authenticated' }, { status: 401 });
    }
    return HttpResponse.json(await withDelay(user));
  }),

  http.post('/api/login', async ({ request }) => {
    const body = (await request.json()) as { user_id: string };
    const user = db.usersWithRoles.find((u) => u.id === body.user_id);
    if (!user) {
      return HttpResponse.json({ message: 'User not found' }, { status: 404 });
    }
    auth.setCurrentUserId(user.id);
    return HttpResponse.json(await withDelay(user));
  }),

  http.get('/api/users', async () => {
    return HttpResponse.json(await withDelay(db.usersWithRoles.filter((u) => u.deleted_at === null)));
  }),

  // Modules endpoints
  http.get('/api/modules', async () => {
    const modules = db.modules.filter((m) => m.deleted_at === null);
    return HttpResponse.json(await withDelay(modules));
  }),

  http.get('/api/modules/:id', async ({ params }) => {
    const module = dbHelpers.getModuleById(params.id as string);
    if (!module) {
      return HttpResponse.json({ message: 'Module not found' }, { status: 404 });
    }
    return HttpResponse.json(await withDelay(module));
  }),

  http.post('/api/modules', async ({ request }) => {
    const body = await request.json();
    const module = dbHelpers.createModule(body as Partial<typeof db.modules[0]>);
    return HttpResponse.json(await withDelay(module), { status: 201 });
  }),

  http.patch('/api/modules/:id', async ({ params, request }) => {
    const body = await request.json();
    const module = dbHelpers.updateModule(params.id as string, body as Partial<typeof db.modules[0]>);
    if (!module) {
      return HttpResponse.json({ message: 'Module not found' }, { status: 404 });
    }
    return HttpResponse.json(await withDelay(module));
  }),

  http.delete('/api/modules/:id', async ({ params }) => {
    const success = dbHelpers.deleteModule(params.id as string);
    if (!success) {
      return HttpResponse.json({ message: 'Module not found' }, { status: 404 });
    }
    return new HttpResponse(null, { status: 204 });
  }),

  // Missions endpoints
  http.get('/api/missions', async ({ request }) => {
    const url = new URL(request.url);
    const moduleId = url.searchParams.get('module_id');
    if (!moduleId) {
      return HttpResponse.json({ message: 'module_id required' }, { status: 400 });
    }
    const missions = dbHelpers.getMissionsByModuleId(moduleId);
    return HttpResponse.json(await withDelay(missions));
  }),

  // Flows endpoints
  http.get('/api/flows', async ({ request }) => {
    const url = new URL(request.url);
    const moduleId = url.searchParams.get('module_id');
    if (!moduleId) {
      return HttpResponse.json(await withDelay(db.flows.filter((f) => f.deleted_at === null)));
    }
    const flows = dbHelpers.getFlowsByModuleId(moduleId);
    return HttpResponse.json(await withDelay(flows));
  }),

  http.get('/api/flows/:id', async ({ params }) => {
    const flow = dbHelpers.getFlowById(params.id as string);
    if (!flow) {
      return HttpResponse.json({ message: 'Flow not found' }, { status: 404 });
    }
    return HttpResponse.json(await withDelay(flow));
  }),

  // Lessons endpoints
  http.get('/api/lessons', async ({ request }) => {
    const url = new URL(request.url);
    const flowId = url.searchParams.get('flow_id');
    if (!flowId) {
      return HttpResponse.json({ message: 'flow_id required' }, { status: 400 });
    }
    const lessons = dbHelpers.getLessonsByFlowId(flowId);
    return HttpResponse.json(await withDelay(lessons));
  }),

  // Tasks endpoints
  http.get('/api/tasks', async ({ request }) => {
    const url = new URL(request.url);
    const moduleId = url.searchParams.get('module_id');
    const flowId = url.searchParams.get('flow_id') || undefined;
    
    if (!moduleId) {
      // Return all tasks for admin
      return HttpResponse.json(await withDelay(db.tasks.filter((t) => t.deleted_at === null)));
    }
    
    const tasks = dbHelpers.getTasksByModuleId(moduleId, flowId);
    return HttpResponse.json(await withDelay(tasks));
  }),

  http.get('/api/tasks/:id', async ({ params }) => {
    const task = dbHelpers.getTaskById(params.id as string);
    if (!task) {
      return HttpResponse.json({ message: 'Task not found' }, { status: 404 });
    }
    return HttpResponse.json(await withDelay(task));
  }),

  http.post('/api/tasks', async ({ request }) => {
    const body = await request.json();
    const task = dbHelpers.createTask(body as Partial<typeof db.tasks[0]>);
    return HttpResponse.json(await withDelay(task), { status: 201 });
  }),

  http.patch('/api/tasks/:id', async ({ params, request }) => {
    const body = await request.json();
    const task = dbHelpers.updateTask(params.id as string, body as Partial<typeof db.tasks[0]>);
    if (!task) {
      return HttpResponse.json({ message: 'Task not found' }, { status: 404 });
    }
    return HttpResponse.json(await withDelay(task));
  }),

  http.delete('/api/tasks/:id', async ({ params }) => {
    const success = dbHelpers.deleteTask(params.id as string);
    if (!success) {
      return HttpResponse.json({ message: 'Task not found' }, { status: 404 });
    }
    return new HttpResponse(null, { status: 204 });
  }),

  // Progress endpoints
  http.get('/api/user_task_progress', async ({ request }) => {
    const url = new URL(request.url);
    const userId = url.searchParams.get('user_id');
    const moduleId = url.searchParams.get('module_id') || undefined;
    
    if (!userId) {
      return HttpResponse.json({ message: 'user_id required' }, { status: 400 });
    }
    
    const progress = dbHelpers.getProgressByUser(userId, moduleId);
    return HttpResponse.json(await withDelay(progress));
  }),

  http.post('/api/user_task_progress', async ({ request }) => {
    const body = await request.json();
    const progress = dbHelpers.createProgress(body as Partial<typeof db.userTaskProgress[0]>);
    return HttpResponse.json(await withDelay(progress), { status: 201 });
  }),

  http.patch('/api/user_task_progress/:id', async ({ params, request }) => {
    const body = await request.json();
    const progress = dbHelpers.updateProgress(
      params.id as string,
      body as Partial<typeof db.userTaskProgress[0]>
    );
    if (!progress) {
      return HttpResponse.json({ message: 'Progress not found' }, { status: 404 });
    }
    return HttpResponse.json(await withDelay(progress));
  }),

  // Chat sessions endpoints
  http.get('/api/chat_sessions', async ({ request }) => {
    const url = new URL(request.url);
    const userId = url.searchParams.get('user_id');
    const moduleId = url.searchParams.get('module_id') || undefined;
    const flowId = url.searchParams.get('flow_id') || undefined;
    
    if (!userId) {
      return HttpResponse.json({ message: 'user_id required' }, { status: 400 });
    }
    
    const sessions = dbHelpers.getChatSessions(userId, moduleId, flowId);
    return HttpResponse.json(await withDelay(sessions));
  }),

  http.post('/api/chat_sessions', async ({ request }) => {
    const body = (await request.json()) as { user_id: string; module_id: string; flow_id?: string };
    
    // Check for existing active session
    const existingSession = dbHelpers.getActiveChatSession(
      body.user_id,
      body.module_id,
      body.flow_id
    );
    
    if (existingSession) {
      return HttpResponse.json(await withDelay(existingSession));
    }
    
    const session = dbHelpers.createChatSession(body);
    
    // Add welcome message
    const module = dbHelpers.getModuleById(body.module_id);
    const assistant = db.assistantProfiles.find((a) => a.module_id === body.module_id);
    
    dbHelpers.createMessage({
      chat_session_id: session.id,
      sender_type: 'system',
      content: `Добро пожаловать в чат${assistant ? ` с ${assistant.name}` : ''}! ${
        module ? `Задавайте вопросы по модулю "${module.title}".` : ''
      }`,
    });
    
    return HttpResponse.json(await withDelay(session), { status: 201 });
  }),

  http.patch('/api/chat_sessions/:id', async ({ params, request }) => {
    const body = await request.json();
    if ((body as { ended_at?: string }).ended_at) {
      const session = dbHelpers.endChatSession(params.id as string);
      if (!session) {
        return HttpResponse.json({ message: 'Session not found' }, { status: 404 });
      }
      return HttpResponse.json(await withDelay(session));
    }
    return HttpResponse.json({ message: 'Invalid update' }, { status: 400 });
  }),

  // Messages endpoints
  http.get('/api/messages', async ({ request }) => {
    const url = new URL(request.url);
    const sessionId = url.searchParams.get('chat_session_id');
    
    if (!sessionId) {
      return HttpResponse.json({ message: 'chat_session_id required' }, { status: 400 });
    }
    
    const messages = dbHelpers.getMessagesBySessionId(sessionId);
    return HttpResponse.json(await withDelay(messages));
  }),

  http.post('/api/messages', async ({ request }) => {
    const body = (await request.json()) as {
      chat_session_id: string;
      sender_type: 'user' | 'assistant' | 'system';
      content: string;
    };
    
    const userMessage = dbHelpers.createMessage(body);
    
    // If user message, generate mock assistant response
    if (body.sender_type === 'user') {
      await delay(1000); // Simulate assistant "thinking"
      
      const randomResponse = assistantResponses[Math.floor(Math.random() * assistantResponses.length)];
      const assistantMessage = dbHelpers.createMessage({
        chat_session_id: body.chat_session_id,
        sender_type: 'assistant',
        content: `${randomResponse}\n\nВаш вопрос: "${body.content}"\n\nЭто мок-ответ ассистента. В реальной системе здесь будет интеллектуальный ответ от LangFlow.`,
      });
      
      return HttpResponse.json(await withDelay([userMessage, assistantMessage]), { status: 201 });
    }
    
    return HttpResponse.json(await withDelay(userMessage), { status: 201 });
  }),

  // Assistant profiles endpoints
  http.get('/api/assistant_profiles', async ({ request }) => {
    const url = new URL(request.url);
    const moduleId = url.searchParams.get('module_id');
    
    if (!moduleId) {
      return HttpResponse.json(
        await withDelay(db.assistantProfiles.filter((a) => a.deleted_at === null))
      );
    }
    
    const assistants = dbHelpers.getAssistantsByModuleId(moduleId);
    return HttpResponse.json(await withDelay(assistants));
  }),

  http.get('/api/assistant_profiles/:id', async ({ params }) => {
    const assistant = db.assistantProfiles.find(
      (a) => a.id === params.id && a.deleted_at === null
    );
    if (!assistant) {
      return HttpResponse.json({ message: 'Assistant not found' }, { status: 404 });
    }
    return HttpResponse.json(await withDelay(assistant));
  }),

  http.post('/api/assistant_profiles', async ({ request }) => {
    const body = await request.json();
    const assistant = dbHelpers.createAssistant(body as Partial<typeof db.assistantProfiles[0]>);
    return HttpResponse.json(await withDelay(assistant), { status: 201 });
  }),

  http.patch('/api/assistant_profiles/:id', async ({ params, request }) => {
    const body = await request.json();
    const assistant = dbHelpers.updateAssistant(
      params.id as string,
      body as Partial<typeof db.assistantProfiles[0]>
    );
    if (!assistant) {
      return HttpResponse.json({ message: 'Assistant not found' }, { status: 404 });
    }
    return HttpResponse.json(await withDelay(assistant));
  }),

  http.delete('/api/assistant_profiles/:id', async ({ params }) => {
    const success = dbHelpers.deleteAssistant(params.id as string);
    if (!success) {
      return HttpResponse.json({ message: 'Assistant not found' }, { status: 404 });
    }
    return new HttpResponse(null, { status: 204 });
  }),
];

