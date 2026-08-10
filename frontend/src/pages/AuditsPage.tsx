import { useCallback, useEffect, useState } from 'react';
import { PolicyNotice } from '../components/PolicyNotice';
import {
  ApiError,
  api,
  type AuditRecord,
  type Finding,
  type StoredAudit,
} from '../lib/api';

const VERDICT_LABEL: Record<string, string> = {
  pass: 'Correcto',
  warning: 'Atención',
  fail: 'Crítico',
};

const SEVERITY_ORDER: Record<Finding['status'], number> = {
  fail: 0,
  warning: 1,
  pass: 2,
};

function FindingList({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return <p className="muted">Sin hallazgos en los chequeos aplicados.</p>;
  }

  // Most severe first: an operator reads the top and stops.
  const sorted = [...findings].sort(
    (a, b) => SEVERITY_ORDER[a.status] - SEVERITY_ORDER[b.status],
  );

  return (
    <ul className="finding-list">
      {sorted.map((finding, index) => (
        <li className={`finding finding--${finding.status}`} key={`${finding.name}-${index}`}>
          <span className="finding__label">{VERDICT_LABEL[finding.status]}</span>
          <div>
            <strong>{finding.name}</strong>
            <p>{finding.message}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function ReportModal({ audit, onClose }: { audit: StoredAudit; onClose: () => void }) {
  const payload = audit.payload;

  return (
    <div className="modal" onClick={onClose} role="presentation">
      <div className="modal__panel" onClick={(event) => event.stopPropagation()}>
        <div className="modal__head">
          <div>
            <h2>Informe #{audit.id}</h2>
            <p className="muted">{new Date(audit.started_at).toLocaleString()}</p>
          </div>
          <button className="button button--ghost" onClick={onClose} type="button">
            ✕
          </button>
        </div>

        <div className="modal__facts">
          <div>
            <span className="muted">Resultado</span>
            <strong className={`chip chip--${audit.verdict}`}>
              {VERDICT_LABEL[audit.verdict]}
            </strong>
          </div>
          <div>
            <span className="muted">Tipo</span>
            <strong>{audit.audit_type}</strong>
          </div>
          <div>
            <span className="muted">Objetivo</span>
            <strong>{audit.target}</strong>
          </div>
          {audit.client ? (
            <div>
              <span className="muted">Cliente</span>
              <strong>{audit.client}</strong>
            </div>
          ) : null}
        </div>

        {audit.summary ? <p>{audit.summary}</p> : null}

        <div className="modal__actions">
          <button
            className="button button--secondary"
            onClick={() => void api.downloadReport(audit.assessment_id, 'pdf')}
            type="button"
          >
            Descargar PDF
          </button>
          <button
            className="button button--ghost"
            onClick={() => void api.downloadReport(audit.assessment_id, 'md')}
            type="button"
          >
            Markdown
          </button>
        </div>

        <h3>Hallazgos</h3>
        <FindingList findings={payload?.findings ?? []} />

        {payload?.trace ? (
          <>
            <h3>Traza de conexión</h3>
            <p>{payload.trace.summary}</p>
            <ol className="chain__hops">
              {payload.trace.hops.map((hop, index) => (
                <li className="chain__hop" key={`${hop.name}-${index}`}>
                  <div className="chain__hop-head">
                    <span className="chain__role">{hop.role}</span>
                    <strong>{hop.name}</strong>
                    {hop.port ? <span className="chain__port">puerto {hop.port}</span> : null}
                  </div>
                  <p className="muted">{hop.evidence}</p>
                </li>
              ))}
            </ol>
          </>
        ) : null}

        {payload?.unreachable?.length ? (
          <>
            <h3>Alcance no cubierto</h3>
            <ul className="muted">
              {payload.unreachable.map((item) => (
                <li key={item.device}>
                  {item.device}: {item.reason}
                </li>
              ))}
            </ul>
          </>
        ) : null}
      </div>
    </div>
  );
}

/** Audit history and the button that runs a new one. */
export function AuditsPage() {
  const [audits, setAudits] = useState<AuditRecord[]>([]);
  const [open, setOpen] = useState<StoredAudit | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [running, setRunning] = useState(false);
  const [typeFilter, setTypeFilter] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('');
  const [client, setClient] = useState('');
  const [target, setTarget] = useState('');

  const load = useCallback(async () => {
    try {
      setAudits(
        await api.listAudits({
          audit_type: typeFilter || undefined,
          verdict: verdictFilter || undefined,
        }),
      );
      setError(null);
    } catch (cause) {
      setError(cause as ApiError);
    }
  }, [typeFilter, verdictFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  async function runAudit() {
    setRunning(true);
    setError(null);
    try {
      await api.runAudit({
        client,
        trace_target: target || undefined,
        locale: 'es',
      });
      await load();
    } catch (cause) {
      setError(cause as ApiError);
    } finally {
      setRunning(false);
    }
  }

  async function openReport(audit: AuditRecord) {
    try {
      setOpen(await api.getAudit(audit.id));
    } catch (cause) {
      setError(cause as ApiError);
    }
  }

  return (
    <div className="stack">
      {error ? <PolicyNotice error={error} /> : null}

      <section className="panel">
        <div className="toolbar">
          <select onChange={(e) => setTypeFilter(e.target.value)} value={typeFilter}>
            <option value="">Todos los tipos</option>
            <option value="network">Red</option>
            <option value="trace">Traza</option>
            <option value="device">Dispositivo</option>
          </select>
          <select onChange={(e) => setVerdictFilter(e.target.value)} value={verdictFilter}>
            <option value="">Todos los resultados</option>
            <option value="pass">Correcto</option>
            <option value="warning">Atención</option>
            <option value="fail">Crítico</option>
          </select>
          <input
            className="toolbar__search"
            onChange={(event) => setClient(event.target.value)}
            placeholder="Cliente o sitio"
            value={client}
          />
          <input
            className="toolbar__search"
            onChange={(event) => setTarget(event.target.value)}
            placeholder="Endpoint a rastrear (opcional)"
            value={target}
          />
          <button
            className="button button--primary"
            disabled={running}
            onClick={() => void runAudit()}
            type="button"
          >
            {running ? 'Ejecutando…' : 'Nueva auditoría'}
          </button>
        </div>

        {audits.length === 0 ? (
          <p className="muted">
            Todavía no hay auditorías registradas. Ejecuta la primera con el botón de
            arriba.
          </p>
        ) : (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Objetivo</th>
                  <th>Tipo</th>
                  <th>Hallazgos</th>
                  <th>Resultado</th>
                  <th aria-label="Acciones" />
                </tr>
              </thead>
              <tbody>
                {audits.map((audit) => (
                  <tr key={audit.id}>
                    <td>{new Date(audit.started_at).toLocaleString()}</td>
                    <td>
                      {audit.target}
                      {audit.client ? <div className="muted">{audit.client}</div> : null}
                    </td>
                    <td>{audit.audit_type}</td>
                    <td>
                      {audit.issues_total} de {audit.checks_total}
                    </td>
                    <td>
                      <span className={`chip chip--${audit.verdict}`}>
                        {VERDICT_LABEL[audit.verdict]}
                      </span>
                    </td>
                    <td className="actions">
                      <button
                        className="button button--secondary"
                        onClick={() => void openReport(audit)}
                        type="button"
                      >
                        Ver informe
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {open ? <ReportModal audit={open} onClose={() => setOpen(null)} /> : null}
    </div>
  );
}
