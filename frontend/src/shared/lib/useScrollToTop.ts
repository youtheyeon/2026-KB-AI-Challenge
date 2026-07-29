import { useEffect } from 'react';

export const useScrollToTop = (...deps: unknown[]) => {
  useEffect(() => {
    window.scrollTo(0, 0);
  }, deps);
};
