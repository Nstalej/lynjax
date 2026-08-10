import { useCallback, useEffect, useState } from 'react';
import { PolicyNotice } from '../components/PolicyNotice';
import { TopologyMap } from '../components/TopologyMap';
import { ApiError, api, type DashboardSummary, type Topology } from '../lib/api';

const VERDICT_LABEL: Record<string, string> = {
  pass: 'Correcto',
  warning: 'Atención',
  fail: 'Crítico',
};

function Metric({
  label,
  value,
  tone = 'neutral',
  hint,
}: {
  label: string;
  value: string | number;
  tone?: 'neutral' | 'ok' | 'warn' | 'bad';
  hint?: string;
}) {
  return (
    <div className={`metric metric--${tone}`}>
      <span className="metric__label">{label}</span>
      <strong className="metric__value">{value}</strong>
      {hint ? <span className="metric__hint">{hint}</span> : null}
    </div>
  );
}

/** The operator's first screen: state of the estate, the map, recent activity. */
export function DashboardPage({ onNavigate }: { onNavigate: (id: string) => void }) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [topology, setTopology] = useState<Topology | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [mapping, setMapping] = useState(false);

  const load = useCallback(async () => {
    try {
      setSummary(await api.dashboard());
      setError(null);
    } catch (cause) {
      setError(cause as ApiError);
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 30_000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function drawMap() {
    setMapping(true);
    try {
      setTopology(await api.topology());
      setError(null);
    } catch (cause) {
      setError(cause as ApiError);
    } finally {
      setMapping(false);
    }
  }

  if (!summary) {
    return <p className="muted">Cargando…</p>;
  }

  const { devices, audits } = summary;
  const healthTone =
    summary.health_score === null
      ? 'neutral'
      : summary.health_score >= 80
        ? 'ok'
        : summary.health_score >= 50
          ? 'warn'
          : 'bad';

  return (
    <div className="stack">
      {error ? <PolicyNotice error={error} /> : null}

      <section className="metric-row">
        <Metric
          label="Dispositivos"
          value={devices.total}
          hint={`${devices.active} activos`}
        />
        <Metric label="En línea" value={devices.by_status.online} tone="ok" />
        <Metric label="Con avisos" value={devices.by_status.warning} tone="warn" />
        <Metric label="Sin respuesta" value={devices.by_status.offline} tone="bad" />
        <Metric
          label="Salud de red"
          /* Null until something has been polled. A score of 100% for an
             inventory nobody checked would be a lie by omission. */
          value={summary.health_score === null ? '—' : `${summary.health_score}%`}
          tone={healthTone}
          hint={summary.health_basis}
        />
        <Metric
          label="Agentes"
          value={`${summary.agents.online}/${summary.agents.total}`}
        />
      </section>

      <section className="panel">
        <div className="panel__head">
          <h2>Topología</h2>
          <button
            className="button button--secondary"
            disabled={mapping}
            onClick={() => void drawMap()}
            type="button"
          >
            {mapping ? 'Recolectando…' : 'Actualizar mapa'}
          </button>
        </div>

        {topology ? (
          <TopologyMap topology={topology} />
        ) : (
          <p className="muted">
            El mapa se construye recolectando de los dispositivos activos. Pulsa
            actualizar para trazarlo.
          </p>
        )}
      </section>

      <section className="panel">
        <div className="panel__head">
          <h2>Actividad reciente</h2>
          <button
            className="button button--ghost"
            onClick={() => onNavigate('audits')}
            type="button"
          >
            Ver auditorías
          </button>
        </div>

        {audits.recent.length === 0 ? (
          <p className="muted">Todavía no se ha ejecutado ninguna auditoría.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Objetivo</th>
                <th>Tipo</th>
                <th>Hallazgos</th>
                <th>Resultado</th>
              </tr>
            </thead>
            <tbody>
              {audits.recent.map((item) => (
                <tr key={item.assessment_id}>
                  <td>{new Date(item.started_at).toLocaleString()}</td>
                  <td>{item.target}</td>
                  <td>{item.audit_type}</td>
                  <td>{item.issues_total}</td>
                  <td>
                    <span className={`chip chip--${item.verdict}`}>
                      {VERDICT_LABEL[item.verdict] ?? item.verdict}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
