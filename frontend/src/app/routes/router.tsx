import { createBrowserRouter } from 'react-router';

import { LandingPage } from '@/pages/landing';
import { LoginPage } from '@/pages/login';
import { ROUTES } from '@/shared/config/routes';

export const router = createBrowserRouter([
  {
    path: ROUTES.home,
    Component: LandingPage,
  },
  {
    path: ROUTES.login,
    Component: LoginPage,
  },
]);
