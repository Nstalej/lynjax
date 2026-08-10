import { useState } from 'react';
import { ApiError, api, type Account } from '../lib/api';

/**
 * Sign-in.
 *
 * Centred, on a moving field of nodes and links. The previous version sat in a
 * corner with no background, which read as a debug form rather than the front
 * door of a tool someone puts in front of a client.
 *
 * The animation is CSS only and respects `prefers-reduced-motion`: a login
 * screen is not worth a canvas loop, and motion is not worth a headache.
 */
export function LoginScreen({ onSignedIn }: { onSignedIn: (account: Account) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(email, password);
      onSignedIn(await api.me());
    } catch (cause) {
      setError(cause as ApiError);
    } finally {
      setBusy(false);
    }
  }

  // 409 means the install has no accounts yet. That is a setup step needing the
  // CLI, not a wrong password, so it gets its own instruction.
  const needsBootstrap = error?.status === 409;

  return (
    <div className="login">
      <div aria-hidden="true" className="login__field">
        {Array.from({ length: 18 }).map((_, index) => (
          <span className={`login__node login__node--${index % 6}`} key={index} />
        ))}
        <div className="login__glow" />
      </div>

      <main className="login__panel">
        <div className="login__brand">
          <span className="login__mark" aria-hidden="true" />
          <div>
            <h1>Lynjax</h1>
            <p>Intelligent Network Visibility</p>
          </div>
        </div>

        <form className="login__form" onSubmit={submit}>
          <label className="field">
            <span>Correo</span>
            <input
              autoComplete="username"
              autoFocus
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>

          <label className="field">
            <span>Contraseña</span>
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
              <strong>
                {needsBootstrap ? 'Instalación sin cuentas' : 'No se pudo entrar'}
              </strong>
              <p>{error.message}</p>
              {needsBootstrap ? (
                <code>lynjax user tu@correo.com --admin</code>
              ) : null}
            </div>
          ) : null}

          <button className="button button--primary" disabled={busy} type="submit">
            {busy ? 'Entrando…' : 'Entrar'}
          </button>
        </form>

        <p className="login__footnote">
          El acceso real a la red permanece desactivado hasta habilitarlo de forma
          explícita.
        </p>
      </main>
    </div>
  );
}
