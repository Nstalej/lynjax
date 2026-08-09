import { ApiError } from '../lib/api';

/**
 * Explains an API failure.
 *
 * A policy refusal is deliberately not styled as an error. Lynjax is doing what
 * it was configured to do, and presenting that as a fault would push an
 * operator toward switching the guard off without understanding it.
 */
export function PolicyNotice({ error }: { error: ApiError }) {
  if (error.isPolicyRefusal) {
    return (
      <div className="notice notice--policy" role="status">
        <strong>El acceso real a la red está desactivado.</strong>
        <p>{error.message}</p>
        <p className="muted">
          Actívalo solo para una red que tengas autorización escrita de evaluar:
          <code> LYNJAX_NETWORK_POLICY=authorized-targets</code>
        </p>
      </div>
    );
  }

  return (
    <div className="notice notice--error" role="alert">
      <strong>No se pudo completar la operación.</strong>
      <p>{error.message}</p>
    </div>
  );
}
