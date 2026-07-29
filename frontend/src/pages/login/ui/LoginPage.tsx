import { LoginForm } from '@/features/login';

import { Header } from './Header';

export const LoginPage = () => {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <Header />
      <main className="flex flex-1 items-center justify-center px-6 py-12">
        <LoginForm />
      </main>
    </div>
  );
};
