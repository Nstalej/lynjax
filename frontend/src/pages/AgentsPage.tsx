import { useCallback, useEffect, useState } from 'react';
import { PolicyNotice } from '../components/PolicyNotice';
import { ApiError, api, type AgentRecord } from '../lib/api';

const STATUS_LABEL: Record<AgentRecord['status'], string> = {
  online: 'En línea',
  offline: 'Sin señal',
  unknown: 'Sin registrar señal',
};

/**
 * Remote agents.
 *
 * The Windows AD collector is not ported yet. The screen says so plainly rather
 * than offering a download that would not work: an empty list with a dead button
 * is worse than an honest note about what is coming.
 */
export function AgentsPage() {
  const [agents, setAgents] = useState<AgentRecord[]>([]);
  const [error, setError] = useState<ApiError | null>(null);

  const load = useCallback(async () => {
    try {
      setAgents(await api.listAgents());
      setError(null);
    } catch (cause) {
      setError(cause as ApiError);
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 20_000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function remove(agent: AgentRecord) {
    try {
      await api.deleteAgent(agent.agent_id);
      await load();
    } catch (cause) {
      setError(cause as ApiError);
    }
  }

  return (
    <div className="stack">
      {error ? <PolicyNotice error={error} /> : null}

      <section className="panel">
        <div className="panel__head">
          <h2>Agentes registrados</h2>
          <span className="muted">
            {agents.filter((a) => a.status === 'online').length} en línea de{' '}
            {agents.length}
          </span>
        </div>

        {agents.length === 0 ? (
          <p className="muted">
            Ningún agente registrado. Los agentes permiten auditar Active Directory
            desde dentro de una red aislada.
          </p>
        ) : (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Host</th>
                  <th>Tipo</th>
                  <th>Estado</th>
                  <th>Última señal</th>
                  <th aria-label="Acciones" />
                </tr>
              </thead>
              <tbody>
                {agents.map((agent) => (
                  <tr key={agent.agent_id}>
                    <td>
                      <strong>{agent.name}</strong>
                      {agent.version ? (
                        <div className="muted">v{agent.version}</div>
                      ) : null}
                    </td>
                    <td>{agent.host}</td>
                    <td>{agent.agent_type}</td>
                    <td>
                      <span className={`chip chip--status-${agent.status}`}>
                        {STATUS_LABEL[agent.status]}
                      </span>
                    </td>
                    <td>
                      {agent.last_heartbeat
                        ? new Date(agent.last_heartbeat).toLocaleString()
                        : '—'}
                    </td>
                    <td className="actions">
                      <button
                        className="button button--ghost"
                        onClick={() => void remove(agent)}
                        type="button"
                      >
                        Quitar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Desplegar un agente</h2>
        <div className="notice notice--policy">
          <strong>El agente de Windows todavía no está disponible.</strong>
          <p>
            El registro y la señal de vida ya funcionan, así que un agente puede
            conectarse en cuanto exista. El colector de Active Directory está
            planificado para la siguiente versión.
          </p>
          <p className="muted">
            El estado se calcula desde la última señal recibida, no se almacena: un
            proceso caído no puede actualizar una bandera, y ese es justo el caso que
            esta pantalla existe para mostrar.
          </p>
        </div>
      </section>
    </div>
  );
}
