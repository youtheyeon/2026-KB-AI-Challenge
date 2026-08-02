import { createBrowserRouter } from 'react-router';

import { DashboardPage } from '@/pages/dashboard';
import { LandingPage } from '@/pages/landing';
import { LoginPage } from '@/pages/login';
import { SimulationPage } from '@/pages/simulation';
import { VerifyPage } from '@/pages/verify';
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
  {
    path: ROUTES.simulation,
    Component: SimulationPage,
  },
  {
    path: ROUTES.verify,
    Component: VerifyPage,
  },
  {
    path: ROUTES.dashboard,
    Component: DashboardPage,
  },
]);
