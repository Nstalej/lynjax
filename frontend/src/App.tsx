import { useEffect, useState } from 'react';
import { LoginScreen } from './components/LoginScreen';
import { AppShell } from './layout/AppShell';
import { api, session, type Account } from './lib/api';

/**
 * Authentication gate.
 *
 * The whole app sits behind a session. There is no anonymous mode: the API
 * refuses unauthenticated calls, so a UI that rendered without one would only
 * be a screen full of errors.
 */
export function App() {
  const [account, setAccount] = useState<Account | null>(null);
  const [checking, setChecking] = useState(true);

  // A stored token may already be expired or belong to a deleted account, so it
  // is verified against the API rather than trusted for being present.
  useEffect(() => {
    if (!session.token) {
      setChecking(false);
      return;
    }

    api
      .me()
      .then(setAccount)
      .catch(() => session.clear())
      .finally(() => setChecking(false));
  }, []);

  if (checking) {
    return <div className="login-screen">Verificando sesión…</div>;
  }

  if (!account) {
    return <LoginScreen onSignedIn={setAccount} />;
  }

  return (
    <AppShell
      account={account}
      onSignOut={() => {
        api.logout();
        setAccount(null);
      }}
    />
  );
}
