import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, User, ChevronRight, LogIn, UserPlus, Mail, Lock, AlertCircle } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardDescription, CardHeader } from '@/shared/ui/card';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs';
import { Spinner } from '@/shared/ui/spinner';
import { useUsers, useDemoLogin, useLoginWithCredentials, useRegister } from '@/features';
import { cn } from '@/shared/lib/utils';
import { ROLE_LABELS } from '@/shared/constants';
import type { RoleName } from '@/shared/constants';

export function LoginPage() {
  const navigate = useNavigate();
  
  // Demo login state
  const { data: users, isLoading: usersLoading } = useUsers();
  const demoLoginMutation = useDemoLogin();
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  // Real login state
  const loginWithCredentialsMutation = useLoginWithCredentials();
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState<string | null>(null);

  // Registration state
  const registerMutation = useRegister();
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');
  const [regError, setRegError] = useState<string | null>(null);
  const [regSuccess, setRegSuccess] = useState(false);

  // Demo login handler
  const handleDemoLogin = async () => {
    if (!selectedUserId) return;

    try {
      await demoLoginMutation.mutateAsync({ user_id: selectedUserId });
      navigate('/modules');
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  // Real login handler
  const handleRealLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);

    if (!loginUsername || !loginPassword) {
      setLoginError('Заполните все поля');
      return;
    }

    try {
      await loginWithCredentialsMutation.mutateAsync({
        username: loginUsername,
        password: loginPassword,
      });
      navigate('/modules');
    } catch (error) {
      console.error('Login failed:', error);
      setLoginError('Неверный логин или пароль');
    }
  };

  // Registration handler
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegError(null);
    setRegSuccess(false);

    if (!regUsername || !regEmail || !regPassword) {
      setRegError('Заполните все поля');
      return;
    }

    if (regPassword.length < 8) {
      setRegError('Пароль должен быть не менее 8 символов');
      return;
    }

    if (regPassword !== regConfirmPassword) {
      setRegError('Пароли не совпадают');
      return;
    }

    try {
      await registerMutation.mutateAsync({
        username: regUsername,
        email: regEmail,
        password: regPassword,
      });
      setRegSuccess(true);
      // Clear form
      setRegUsername('');
      setRegEmail('');
      setRegPassword('');
      setRegConfirmPassword('');
    } catch (error: unknown) {
      console.error('Registration failed:', error);
      if (error instanceof Error && error.message.includes('already exists')) {
        setRegError('Пользователь с таким именем или email уже существует');
      } else {
        setRegError('Ошибка регистрации. Попробуйте позже.');
      }
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-cyber-grid bg-[size:50px_50px] opacity-20" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[100px]" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/20 rounded-full blur-[100px]" />

      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8 stagger-fade-in">
          <div className="inline-flex items-center justify-center mb-4">
            <div className="relative">
              <Shield className="h-16 w-16 text-primary" />
              <div className="absolute inset-0 blur-xl bg-primary/50" />
            </div>
          </div>
          <h1 className="font-display text-3xl font-bold tracking-wider">
            WIND<span className="text-primary">CHASER</span>
          </h1>
          <p className="text-muted-foreground mt-2">
            Тренажёр по информационной безопасности
          </p>
        </div>

        <Card className="animate-fade-in" style={{ animationDelay: '200ms' }}>
          <Tabs defaultValue="login" className="w-full">
            <CardHeader className="pb-4">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="login" className="flex items-center gap-2">
                  <LogIn className="h-4 w-4" />
                  Вход
                </TabsTrigger>
                <TabsTrigger value="register" className="flex items-center gap-2">
                  <UserPlus className="h-4 w-4" />
                  Регистрация
                </TabsTrigger>
                <TabsTrigger value="demo" className="flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Демо
                </TabsTrigger>
              </TabsList>
            </CardHeader>

            {/* Real Login Tab */}
            <TabsContent value="login">
              <CardContent>
                <form onSubmit={handleRealLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-username">Имя пользователя</Label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="login-username"
                        type="text"
                        placeholder="username"
                        value={loginUsername}
                        onChange={(e) => setLoginUsername(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="login-password">Пароль</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="login-password"
                        type="password"
                        placeholder="********"
                        value={loginPassword}
                        onChange={(e) => setLoginPassword(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>

                  {loginError && (
                    <div className="flex items-center gap-2 text-sm text-destructive">
                      <AlertCircle className="h-4 w-4" />
                      {loginError}
                    </div>
                  )}

                  <Button
                    type="submit"
                    className="w-full"
                    size="lg"
                    disabled={loginWithCredentialsMutation.isPending}
                  >
                    {loginWithCredentialsMutation.isPending ? (
                      <Spinner size="sm" className="mr-2" />
                    ) : (
                      <LogIn className="mr-2 h-4 w-4" />
                    )}
                    Войти
                  </Button>
                </form>
              </CardContent>
            </TabsContent>

            {/* Registration Tab */}
            <TabsContent value="register">
              <CardContent>
                {regSuccess ? (
                  <div className="text-center py-4 space-y-4">
                    <div className="text-primary text-lg font-medium">
                      Регистрация успешна!
                    </div>
                    <p className="text-muted-foreground text-sm">
                      Теперь вы можете войти в систему
                    </p>
                    <Button
                      variant="outline"
                      onClick={() => setRegSuccess(false)}
                    >
                      Зарегистрировать ещё
                    </Button>
                  </div>
                ) : (
                  <form onSubmit={handleRegister} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="reg-username">Имя пользователя</Label>
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="reg-username"
                          type="text"
                          placeholder="username"
                          value={regUsername}
                          onChange={(e) => setRegUsername(e.target.value)}
                          className="pl-10"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="reg-email">Email</Label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="reg-email"
                          type="email"
                          placeholder="email@example.com"
                          value={regEmail}
                          onChange={(e) => setRegEmail(e.target.value)}
                          className="pl-10"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="reg-password">Пароль</Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="reg-password"
                          type="password"
                          placeholder="Минимум 8 символов"
                          value={regPassword}
                          onChange={(e) => setRegPassword(e.target.value)}
                          className="pl-10"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="reg-confirm-password">Подтвердите пароль</Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="reg-confirm-password"
                          type="password"
                          placeholder="Повторите пароль"
                          value={regConfirmPassword}
                          onChange={(e) => setRegConfirmPassword(e.target.value)}
                          className="pl-10"
                        />
                      </div>
                    </div>

                    {regError && (
                      <div className="flex items-center gap-2 text-sm text-destructive">
                        <AlertCircle className="h-4 w-4" />
                        {regError}
                      </div>
                    )}

                    <Button
                      type="submit"
                      className="w-full"
                      size="lg"
                      disabled={registerMutation.isPending}
                    >
                      {registerMutation.isPending ? (
                        <Spinner size="sm" className="mr-2" />
                      ) : (
                        <UserPlus className="mr-2 h-4 w-4" />
                      )}
                      Зарегистрироваться
                    </Button>
                  </form>
                )}
              </CardContent>
            </TabsContent>

            {/* Demo Login Tab */}
            <TabsContent value="demo">
              <CardHeader className="pt-0">
                <CardDescription>
                  Выберите пользователя для входа (демо-режим)
                </CardDescription>
              </CardHeader>
              <CardContent>
                {usersLoading ? (
                  <div className="flex justify-center py-8">
                    <Spinner size="lg" />
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {users?.map((user) => (
                        <button
                          key={user.id}
                          onClick={() => setSelectedUserId(user.id)}
                          className={cn(
                            'w-full flex items-center gap-3 p-3 rounded-lg border transition-all text-left',
                            selectedUserId === user.id
                              ? 'border-primary bg-primary/10 shadow-[0_0_10px_hsl(var(--primary)/0.2)]'
                              : 'border-border/50 hover:border-primary/50 hover:bg-muted/50'
                          )}
                          aria-label={`Выбрать пользователя ${user.username}`}
                        >
                          <div
                            className={cn(
                              'flex h-10 w-10 items-center justify-center rounded-full',
                              selectedUserId === user.id
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-muted text-muted-foreground'
                            )}
                          >
                            <User className="h-5 w-5" />
                          </div>
                          <div className="flex-1">
                            <p className="font-medium">{user.username}</p>
                            <p className="text-xs text-muted-foreground">
                              {user.email}
                            </p>
                          </div>
                          <span
                            className={cn(
                              'text-xs px-2 py-1 rounded-full',
                              user.role?.name === 'admin'
                                ? 'bg-secondary/20 text-secondary'
                                : 'bg-primary/20 text-primary'
                            )}
                          >
                            {ROLE_LABELS[user.role?.name as RoleName] || user.role?.name}
                          </span>
                        </button>
                      ))}
                    </div>

                    <Button
                      className="w-full"
                      size="lg"
                      onClick={handleDemoLogin}
                      disabled={!selectedUserId || demoLoginMutation.isPending}
                    >
                      {demoLoginMutation.isPending ? (
                        <Spinner size="sm" className="mr-2" />
                      ) : (
                        <ChevronRight className="mr-2 h-4 w-4" />
                      )}
                      Войти (демо)
                    </Button>
                  </div>
                )}
              </CardContent>
            </TabsContent>
          </Tabs>
        </Card>

        <p className="text-center text-xs text-muted-foreground mt-6">
          WindChaser Security — образовательная платформа
          <br />
          для обучения безопасности AI-систем
        </p>
      </div>
    </div>
  );
}

