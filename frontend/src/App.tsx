import React, { useState, useEffect, useCallback } from 'react';
import { LandingPage } from './components/landing/LandingPage';
import { Dashboard } from './components/Dashboard';

export type RoutePath = '/' | '/dashboard';

export const App: React.FC = () => {
  const getInitialRoute = (): RoutePath => {
    const path = window.location.pathname;
    const hash = window.location.hash;
    if (path.startsWith('/dashboard') || hash === '#/dashboard' || hash.startsWith('#/dashboard')) {
      return '/dashboard';
    }
    return '/';
  };

  const [currentRoute, setCurrentRoute] = useState<RoutePath>(getInitialRoute);

  useEffect(() => {
    // If entered via legacy #/dashboard hash, canonicalize URL to /dashboard
    if (window.location.hash === '#/dashboard' || window.location.hash.startsWith('#/dashboard')) {
      window.history.replaceState(null, '', '/dashboard');
    }

    const handleRouteChange = () => {
      const path = window.location.pathname;
      const hash = window.location.hash;
      if (path.startsWith('/dashboard') || hash === '#/dashboard' || hash.startsWith('#/dashboard')) {
        setCurrentRoute('/dashboard');
      } else {
        setCurrentRoute('/');
      }
    };

    window.addEventListener('popstate', handleRouteChange);
    window.addEventListener('hashchange', handleRouteChange);

    return () => {
      window.removeEventListener('popstate', handleRouteChange);
      window.removeEventListener('hashchange', handleRouteChange);
    };
  }, []);

  const navigate = useCallback((route: RoutePath) => {
    if (window.location.pathname !== route || window.location.hash) {
      window.history.pushState(null, '', route);
    }
    setCurrentRoute(route);
    window.scrollTo(0, 0);
  }, []);

  return (
    <>
      {currentRoute === '/dashboard' ? (
        <Dashboard onNavigateLanding={() => navigate('/')} />
      ) : (
        <LandingPage onNavigateDashboard={() => navigate('/dashboard')} />
      )}
    </>
  );
};

export default App;
