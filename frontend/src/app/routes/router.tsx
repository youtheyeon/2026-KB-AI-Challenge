import { createBrowserRouter } from 'react-router';

import { LandingPage } from '@/pages/landing';
import { ROUTES } from '@/shared/config/routes';

export const router = createBrowserRouter([
  {
    path: ROUTES.home,
    Component: LandingPage,
  },
]);
