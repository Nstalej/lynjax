import { useState } from 'react';
import { PolicyNotice } from '../components/PolicyNotice';
import { ApiError, api, type AuditResult, type ChainTrace, type Finding } from '../lib/api';

const SEVERITY_LABEL: Record<Finding['status'], string> = {
  fail: 'Crítico',
  warning: 'Atención',
  pass: 'Correcto',
};

function FindingList({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return <p className="muted">Sin hallazgos en los chequeos aplicados.</p>;
  }

  // Most severe first: an operator reads the top of the list and stops.
  const order: Record<Finding['status'], number> = { fail: 0, warning: 1, pass: 2 };
  const sorted = [...findings].sort((a, b) => order[a.status] - order[b.status]);

  return (
    <ul className="finding-list">
      {sorted.map((finding, index) => (
        <li className={`finding finding--${finding.status}`} key={`${finding.name}-${index}`}>
          <span className="finding__label">{SEVERITY_LABEL[finding.status]}</span>
          <div>
            <strong>{finding.name}</strong>
            <p>{finding.message}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function ChainView({ trace }: { trace: ChainTrace }) {
  return (
    <div className="chain">
      <p className="chain__summary">{trace.summary}</p>
      {trace.resolved_mac ? (
        <p className="muted">
          {trace.target} resuelve a <code>{trace.resolved_mac}</code>
        </p>
      ) : null}

      <ol className="chain__hops">
        {trace.hops.map((hop, index) => (
          <li className={`chain__hop chain__hop--${hop.role}`} key={`${hop.name}-${index}`}>
            <div className="chain__hop-head">
              <span className="chain__role">{hop.role}</span>
              <strong>{hop.name}</strong>
              {hop.port ? <span className="chain__port">puerto {hop.port}</span> : null}
            </div>
            <p className="muted">{hop.evidence}</p>
            {hop.findings.filter((f) => f.status !== 'pass').length > 0 ? (
              <FindingList findings={hop.findings.filter((f) => f.status !== 'pass')} />
            ) : null}
          </li>
        ))}
      </ol>

      {trace.findings.length > 0 ? <FindingList findings={trace.findings} /> : null}
    </div>
  );
}

/** Run an assessment, trace an endpoint, and download the report. */
export function AuditPage() {
  const [client, setClient] = useState('');
  const [target, setTarget] = useState('');
  const [result, setResult] = useState<AuditResult | null>(null);
  const [trace, setTrace] = useState<ChainTrace | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [running, setRunning] = useState(false);

  async function runAudit(event: React.FormEvent) {
    event.preventDefault();
    setRunning(true);
    setError(null);
    try {
      const audit = await api.runAudit({
        client,
        trace_target: target || undefined,
        locale: 'es',
      });
      setResult(audit);
      setTrace(audit.trace);
    } catch (cause) {
      setError(cause as ApiError);
      setResult(null);
    } finally {
      setRunning(false);
    }
  }

  async function runTrace(event: React.FormEvent) {
    event.preventDefault();
    setRunning(true);
    setError(null);
    try {
      setTrace(await api.trace(target));
    } catch (cause) {
      setError(cause as ApiError);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="module-stack">
      <section className="module-panel">
        <h2>Auditoría</h2>
        <p>
          Recolecta de cada dispositivo activo, aplica los chequeos entre equipos y
          produce el informe entregable.
        </p>

        <form className="form-inline" onSubmit={runAudit}>
          <label>
            Cliente o sitio
            <input
              onChange={(event) => setClient(event.target.value)}
              placeholder="Dirección General de Caminos"
              value={client}
            />
          </label>
          <label>
            Endpoint a rastrear (opcional)
            <input
              onChange={(event) => setTarget(event.target.value)}
              placeholder="10.0.0.50"
              value={target}
            />
          </label>
          <button className="button button--primary" disabled={running} type="submit">
            {running ? 'Ejecutando…' : 'Ejecutar auditoría'}
          </button>
        </form>

        {error ? <PolicyNotice error={error} /> : null}

        {result ? (
          <div className="audit-result">
            <div className={`verdict verdict--${result.verdict}`}>
              {SEVERITY_LABEL[result.verdict]}
            </div>
            <p>{result.summary}</p>

            <div className="audit-result__actions">
              <a
                className="button button--secondary"
                href={api.reportUrl(result.assessment_id, 'pdf')}
                rel="noreferrer"
                target="_blank"
              >
                Descargar PDF
              </a>
              <a
                className="button button--ghost"
                href={api.reportUrl(result.assessment_id, 'md')}
                rel="noreferrer"
                target="_blank"
              >
                Descargar Markdown
              </a>
            </div>

            <h3>Hallazgos</h3>
            <FindingList findings={result.findings} />

            {result.unreachable.length > 0 ? (
              <>
                <h3>Alcance no cubierto</h3>
                <ul className="muted">
                  {result.unreachable.map((item) => (
                    <li key={item.device}>
                      {item.device}: {item.reason}
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="module-panel">
        <h2>Traza de conexión</h2>
        <p>
          Dado el equipo del que se quejaron, recorre la cadena hasta el borde y señala
          en qué eslabón está el problema.
        </p>

        <form className="form-inline" onSubmit={runTrace}>
          <label>
            IP del endpoint
            <input
              onChange={(event) => setTarget(event.target.value)}
              placeholder="10.0.0.50"
              required
              value={target}
            />
          </label>
          <button className="button button--primary" disabled={running} type="submit">
            {running ? 'Rastreando…' : 'Rastrear'}
          </button>
        </form>

        {trace ? <ChainView trace={trace} /> : null}
      </section>
    </div>
  );
}
