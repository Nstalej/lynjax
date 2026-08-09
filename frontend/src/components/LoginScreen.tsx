import { useState } from 'react';
import { ApiError, api, type Account } from '../lib/api';

/** Sign-in. Authentication is required; there is no anonymous mode. */
export function LoginScreen({ onSignedIn }: { onSignedIn: (account: Account) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(email, password);
      onSignedIn(await api.me());
    } catch (cause) {
      const apiError = cause as ApiError;
      // A 409 means the install has no accounts yet, which needs the CLI. That
      // is a setup step, not a wrong password, so it gets its own message.
      setError(apiError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <p className="eyebrow">Lynjax</p>
        <h1>Iniciar sesión</h1>

        <label>
          Correo
          <input
            autoComplete="username"
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
        </label>

        <label>
          Contraseña
          <input
            autoComplete="current-password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>

        {error ? (
          <div className="notice notice--error" role="alert">
            {error}
          </div>
        ) : null}

        <button className="button button--primary" disabled={busy} type="submit">
          {busy ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}
