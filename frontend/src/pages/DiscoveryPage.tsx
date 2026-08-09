import { useEffect, useRef, useState } from 'react';
import { PolicyNotice } from '../components/PolicyNotice';
import { ApiError, api, type DiscoveryJob } from '../lib/api';

/**
 * Network discovery.
 *
 * The scope warning is deliberately in front of the operator rather than buried
 * in documentation: this is the one screen that reaches addresses nobody
 * registered, and the person clicking it is responsible for having permission.
 */
export function DiscoveryPage() {
  const [subnets, setSubnets] = useState('192.168.1.0/24');
  const [community, setCommunity] = useState('');
  const [job, setJob] = useState<DiscoveryJob | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [starting, setStarting] = useState(false);
  const pollRef = useRef<number | null>(null);

  // Stop polling when the component goes away, or the interval keeps firing
  // against a job nobody is looking at.
  useEffect(() => {
    return () => {
      if (pollRef.current !== null) {
        window.clearInterval(pollRef.current);
      }
    };
  }, []);

  function poll(jobId: string) {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
    }
    pollRef.current = window.setInterval(async () => {
      try {
        const updated = await api.getDiscoveryJob(jobId);
        setJob(updated);
        if (updated.status !== 'running' && pollRef.current !== null) {
          window.clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch {
        if (pollRef.current !== null) {
          window.clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }
    }, 1000);
  }

  async function start(event: React.FormEvent) {
    event.preventDefault();
    setStarting(true);
    setError(null);
    try {
      const started = await api.startDiscovery({
        subnets: subnets
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
        methods: community ? ['tcp', 'ssh', 'snmp'] : ['tcp', 'ssh'],
        snmp_community: community || undefined,
      });
      setJob(started);
      poll(started.job_id);
    } catch (cause) {
      setError(cause as ApiError);
      setJob(null);
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="module-stack">
      <section className="module-panel">
        <h2>Descubrimiento de red</h2>

        <div className="notice notice--policy" role="note">
          <strong>Escanea únicamente redes que tengas autorización de evaluar.</strong>
          <p className="muted">
            El alcance se limita a rangos privados y a un máximo de direcciones. El
            espacio público se rechaza salvo que lo habilites de forma explícita.
          </p>
        </div>

        <form className="form-inline" onSubmit={start}>
          <label>
            Subredes (separadas por coma)
            <input
              onChange={(event) => setSubnets(event.target.value)}
              placeholder="192.168.1.0/24, 10.0.5.0/24"
              required
              value={subnets}
            />
          </label>
          <label>
            Comunidad SNMP (opcional)
            <input
              onChange={(event) => setCommunity(event.target.value)}
              placeholder="deja vacío para omitir SNMP"
              value={community}
            />
          </label>
          <button className="button button--primary" disabled={starting} type="submit">
            {starting ? 'Iniciando…' : 'Escanear'}
          </button>
        </form>

        {error ? <PolicyNotice error={error} /> : null}

        {job ? (
          <div className="discovery-job">
            <div className="discovery-job__head">
              <span className={`verdict verdict--${job.status === 'completed' ? 'pass' : 'warning'}`}>
                {job.status}
              </span>
              <span>
                {job.scanned_hosts} de {job.total_hosts} direcciones ({job.progress_percent}%)
              </span>
              <span>{job.responding_hosts} respondieron</span>
            </div>

            <progress max={100} value={job.progress_percent} />

            {job.error ? <p className="notice notice--error">{job.error}</p> : null}

            {job.results.length > 0 ? (
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Dirección</th>
                      <th>Nombre</th>
                      <th>Puertos</th>
                      <th>Indicio</th>
                      <th>Inventario</th>
                    </tr>
                  </thead>
                  <tbody>
                    {job.results.map((host) => (
                      <tr key={host.ip}>
                        <td>{host.ip}</td>
                        <td>{host.hostname || <span className="muted">—</span>}</td>
                        <td>{host.open_ports.join(', ')}</td>
                        <td>{host.device_hint}</td>
                        <td>
                          {host.already_registered ? (
                            'Registrado'
                          ) : (
                            <span className="muted">Sin registrar</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : job.status !== 'running' ? (
              <p className="muted">Ninguna dirección del alcance respondió.</p>
            ) : null}
          </div>
        ) : null}
      </section>
    </div>
  );
}
