import { useCallback, useEffect, useState } from 'react';
import { StatusBadge } from '../components/ui/StatusBadge';
import type { StatusTone } from '../types/platform';
import { ApiError, api, type ConnectivityCheck, type Device, type NewDevice } from '../lib/api';
import { PolicyNotice } from '../components/PolicyNotice';

/** Device status to the shell's badge vocabulary. */
const STATUS_TONE: Record<Device['status'], StatusTone> = {
  online: 'stable',
  warning: 'watch',
  offline: 'alert',
  unknown: 'neutral',
};

const EMPTY_FORM: NewDevice = {
  name: '',
  host: '',
  connector_type: 'ssh',
  device_type: 'auto',
  credential_name: '',
  description: '',
};

/** Device inventory: register equipment and probe whether it answers. */
export function AssetsPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [form, setForm] = useState<NewDevice>(EMPTY_FORM);
  const [error, setError] = useState<ApiError | null>(null);
  const [checks, setChecks] = useState<Record<number, ConnectivityCheck>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setDevices(await api.listDevices());
      setError(null);
    } catch (cause) {
      setError(cause as ApiError);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function addDevice(event: React.FormEvent) {
    event.preventDefault();
    try {
      await api.createDevice({
        ...form,
        // The API treats an absent credential as "none"; an empty string would
        // be stored as a name that matches nothing.
        credential_name: form.credential_name || null,
        description: form.description || null,
      });
      setForm(EMPTY_FORM);
      setError(null);
      await refresh();
    } catch (cause) {
      setError(cause as ApiError);
    }
  }

  async function probe(device: Device) {
    setBusy(device.id);
    try {
      const result = await api.checkDevice(device.id);
      setChecks((current) => ({ ...current, [device.id]: result }));
      setError(null);
      await refresh();
    } catch (cause) {
      setError(cause as ApiError);
    } finally {
      setBusy(null);
    }
  }

  async function remove(device: Device) {
    try {
      await api.deleteDevice(device.id);
      await refresh();
    } catch (cause) {
      setError(cause as ApiError);
    }
  }

  return (
    <div className="module-stack">
      <section className="module-panel">
        <h2>Inventario de dispositivos</h2>
        <p>
          Equipos registrados para auditoría. El sondeo abre una conexión real, así que
          requiere que la política de red esté habilitada.
        </p>

        {error ? <PolicyNotice error={error} /> : null}

        {loading ? (
          <p>Cargando…</p>
        ) : devices.length === 0 ? (
          <p className="muted">
            Aún no hay dispositivos. Registra el primero con el formulario de abajo.
          </p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Dirección</th>
                  <th>Conector</th>
                  <th>Estado</th>
                  <th>Último sondeo</th>
                  <th aria-label="Acciones" />
                </tr>
              </thead>
              <tbody>
                {devices.map((device) => {
                  const check = checks[device.id];
                  return (
                    <tr key={device.id}>
                      <td>
                        <strong>{device.name}</strong>
                        {device.description ? <div className="muted">{device.description}</div> : null}
                      </td>
                      <td>
                        {device.host}:{device.port}
                      </td>
                      <td>
                        {device.connector_type}
                        {device.device_type !== 'auto' ? ` / ${device.device_type}` : ''}
                      </td>
                      <td>
                        <StatusBadge tone={STATUS_TONE[device.status]}>{device.status}</StatusBadge>
                      </td>
                      <td>
                        {check ? (
                          check.reachable ? (
                            <span>{check.latency_ms} ms</span>
                          ) : (
                            <span className="muted" title={check.error ?? ''}>
                              {check.error?.slice(0, 48) ?? 'sin respuesta'}
                            </span>
                          )
                        ) : (
                          <span className="muted">—</span>
                        )}
                      </td>
                      <td className="actions">
                        <button
                          className="button button--secondary"
                          disabled={busy === device.id}
                          onClick={() => void probe(device)}
                          type="button"
                        >
                          {busy === device.id ? 'Sondeando…' : 'Probar'}
                        </button>
                        <button
                          className="button button--ghost"
                          onClick={() => void remove(device)}
                          type="button"
                        >
                          Eliminar
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="module-panel">
        <h3>Registrar dispositivo</h3>
        <form className="form-grid" onSubmit={addDevice}>
          <label>
            Nombre
            <input
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              required
              value={form.name}
            />
          </label>
          <label>
            Dirección o host
            <input
              onChange={(event) => setForm({ ...form, host: event.target.value })}
              placeholder="10.0.0.1"
              required
              value={form.host}
            />
          </label>
          <label>
            Conector
            <select
              onChange={(event) =>
                setForm({ ...form, connector_type: event.target.value as NewDevice['connector_type'] })
              }
              value={form.connector_type}
            >
              <option value="ssh">SSH</option>
              <option value="snmp">SNMP</option>
              <option value="rest">REST</option>
            </select>
          </label>
          <label>
            Tipo
            <select
              onChange={(event) => setForm({ ...form, device_type: event.target.value })}
              value={form.device_type}
            >
              <option value="auto">Detectar</option>
              <option value="mikrotik">MikroTik</option>
              <option value="cisco">Cisco</option>
            </select>
          </label>
          <label>
            Credencial
            <input
              onChange={(event) => setForm({ ...form, credential_name: event.target.value })}
              placeholder="nombre en el vault"
              value={form.credential_name ?? ''}
            />
          </label>
          <label>
            Descripción
            <input
              onChange={(event) => setForm({ ...form, description: event.target.value })}
              value={form.description ?? ''}
            />
          </label>
          <button className="button button--primary" type="submit">
            Registrar
          </button>
        </form>
      </section>
    </div>
  );
}
