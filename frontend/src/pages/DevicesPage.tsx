import { useCallback, useEffect, useMemo, useState } from 'react';
import { PolicyNotice } from '../components/PolicyNotice';
import {
  ApiError,
  api,
  type ConnectivityCheck,
  type Device,
  type DeviceData,
  type NewDevice,
} from '../lib/api';

const STATUS_LABEL: Record<Device['status'], string> = {
  online: 'En línea',
  offline: 'Sin respuesta',
  warning: 'Aviso',
  unknown: 'Sin revisar',
};

const TABS = [
  { id: 'overview', label: 'Resumen' },
  { id: 'interfaces', label: 'Interfaces' },
  { id: 'arp', label: 'Tabla ARP' },
  { id: 'mac', label: 'Tabla MAC' },
  { id: 'routes', label: 'Rutas' },
  { id: 'system', label: 'Sistema' },
] as const;

type TabId = (typeof TABS)[number]['id'];

const EMPTY_FORM: NewDevice = {
  name: '',
  host: '',
  connector_type: 'ssh',
  device_type: 'auto',
  credential_name: '',
  description: '',
};

function formatSpeed(speed: number | null): string {
  if (!speed) return '—';
  if (speed >= 1_000_000_000) return `${speed / 1_000_000_000} Gbps`;
  return `${Math.round(speed / 1_000_000)} Mbps`;
}

/** Device detail: the tables a technician actually reads. */
function DeviceDetail({ device, onClose }: { device: Device; onClose: () => void }) {
  const [tab, setTab] = useState<TabId>('overview');
  const [data, setData] = useState<DeviceData | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);
  const [check, setCheck] = useState<ConnectivityCheck | null>(null);

  const collect = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.deviceData(device.id));
    } catch (cause) {
      setError(cause as ApiError);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [device.id]);

  useEffect(() => {
    void collect();
  }, [collect]);

  async function probe() {
    try {
      setCheck(await api.checkDevice(device.id));
      setError(null);
    } catch (cause) {
      setError(cause as ApiError);
    }
  }

  return (
    <section className="panel">
      <div className="detail__head">
        <div>
          <h2>{device.name}</h2>
          <p className="muted">
            {device.host}:{device.port} · {device.connector_type}
            {device.device_type !== 'auto' ? ` · ${device.device_type}` : ''}
          </p>
        </div>
        <div className="detail__actions">
          <button className="button button--secondary" onClick={() => void probe()} type="button">
            Probar
          </button>
          <button
            className="button button--secondary"
            disabled={loading}
            onClick={() => void collect()}
            type="button"
          >
            {loading ? 'Recolectando…' : 'Actualizar'}
          </button>
          <button className="button button--ghost" onClick={onClose} type="button">
            Cerrar
          </button>
        </div>
      </div>

      {error ? <PolicyNotice error={error} /> : null}

      {check ? (
        <p className={`chip chip--${check.reachable ? 'pass' : 'fail'}`}>
          {check.reachable
            ? `Responde en ${check.latency_ms} ms`
            : (check.error ?? 'Sin respuesta')}
        </p>
      ) : null}

      {/* A collection that came back empty says so. Blank tables with no
          explanation is how a broken collection reads as a healthy device. */}
      {data && !data.collected ? (
        <div className="notice notice--error">
          <strong>El dispositivo no entregó datos.</strong>
          <p>{data.error ?? 'No respondió a ninguna consulta.'}</p>
        </div>
      ) : null}

      <div className="tabs">
        {TABS.map((item) => (
          <button
            className={`tab ${tab === item.id ? 'tab--active' : ''}`}
            key={item.id}
            onClick={() => setTab(item.id)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </div>

      {!data ? (
        <p className="muted">{loading ? 'Recolectando…' : 'Sin datos.'}</p>
      ) : (
        <div className="tab-body">
          {tab === 'overview' ? (
            <dl className="facts">
              <div>
                <dt>Nombre</dt>
                <dd>{device.name}</dd>
              </div>
              <div>
                <dt>Dirección</dt>
                <dd>{device.host}</dd>
              </div>
              <div>
                <dt>Conector</dt>
                <dd>{device.connector_type}</dd>
              </div>
              <div>
                <dt>Estado</dt>
                <dd>{STATUS_LABEL[device.status]}</dd>
              </div>
              <div>
                <dt>Interfaces</dt>
                <dd>
                  {data.interfaces.filter((i) => i.status === 'up').length} de{' '}
                  {data.interfaces.length} activas
                </dd>
              </div>
              <div>
                <dt>Última conexión</dt>
                <dd>{device.last_seen ?? '—'}</dd>
              </div>
            </dl>
          ) : null}

          {tab === 'interfaces' ? (
            <Table
              empty="El dispositivo no reportó interfaces."
              head={['Nombre', 'Estado', 'Velocidad', 'MAC', 'RX', 'TX', 'Errores']}
              rows={data.interfaces.map((item) => [
                item.name,
                <span className={`chip chip--${item.status === 'up' ? 'pass' : 'fail'}`}>
                  {item.status}
                </span>,
                formatSpeed(item.speed),
                item.mac ?? '—',
                item.rx_bytes.toLocaleString(),
                item.tx_bytes.toLocaleString(),
                item.errors > 0 ? <strong className="bad">{item.errors}</strong> : '0',
              ])}
            />
          ) : null}

          {tab === 'arp' ? (
            <Table
              empty="Sin entradas ARP."
              head={['Dirección IP', 'MAC', 'Interfaz', 'Tipo']}
              rows={data.arp.map((item) => [
                item.ip,
                item.mac,
                item.interface,
                item.type,
              ])}
            />
          ) : null}

          {tab === 'mac' ? (
            <Table
              empty="Sin tabla MAC. Los routers no la tienen; los switches sí."
              head={['MAC', 'Puerto', 'VLAN', 'Tipo']}
              rows={data.mac.map((item) => [
                item.mac,
                item.port,
                item.vlan === 0 ? '—' : item.vlan,
                item.type,
              ])}
            />
          ) : null}

          {tab === 'routes' ? (
            <Table
              empty="Sin rutas."
              head={['Destino', 'Puerta de enlace', 'Interfaz', 'Métrica', 'Protocolo']}
              rows={data.routes.map((item) => [
                item.destination,
                item.gateway,
                item.interface || '—',
                item.metric,
                item.protocol,
              ])}
            />
          ) : null}

          {tab === 'system' ? (
            <dl className="facts">
              {Object.entries(data.system).length === 0 ? (
                <p className="muted">Sin información de sistema.</p>
              ) : (
                Object.entries(data.system).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key}</dt>
                    <dd>{String(value) || '—'}</dd>
                  </div>
                ))
              )}
            </dl>
          ) : null}
        </div>
      )}
    </section>
  );
}

function Table({
  head,
  rows,
  empty,
}: {
  head: string[];
  rows: React.ReactNode[][];
  empty: string;
}) {
  if (rows.length === 0) {
    return <p className="muted">{empty}</p>;
  }

  return (
    <div className="table-scroll">
      <table className="table">
        <thead>
          <tr>
            {head.map((label) => (
              <th key={label}>{label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((cells, index) => (
            <tr key={index}>
              {cells.map((cell, cellIndex) => (
                <td key={cellIndex}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [selected, setSelected] = useState<Device | null>(null);
  const [search, setSearch] = useState('');
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState<NewDevice>(EMPTY_FORM);
  const [error, setError] = useState<ApiError | null>(null);

  const load = useCallback(async () => {
    try {
      setDevices(await api.listDevices());
      setError(null);
    } catch (cause) {
      setError(cause as ApiError);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return devices;
    return devices.filter((device) =>
      [device.name, device.host, device.connector_type, device.device_type]
        .join(' ')
        .toLowerCase()
        .includes(needle),
    );
  }, [devices, search]);

  async function addDevice(event: React.FormEvent) {
    event.preventDefault();
    try {
      await api.createDevice({
        ...form,
        credential_name: form.credential_name || null,
        description: form.description || null,
      });
      setForm(EMPTY_FORM);
      setAdding(false);
      await load();
    } catch (cause) {
      setError(cause as ApiError);
    }
  }

  async function remove(device: Device) {
    try {
      await api.deleteDevice(device.id);
      if (selected?.id === device.id) setSelected(null);
      await load();
    } catch (cause) {
      setError(cause as ApiError);
    }
  }

  if (selected) {
    return <DeviceDetail device={selected} onClose={() => setSelected(null)} />;
  }

  return (
    <div className="stack">
      {error ? <PolicyNotice error={error} /> : null}

      <section className="panel">
        {/* Search sits above the table: looking for a device is the first thing
            someone does here, so it should not be below what they are scanning. */}
        <div className="toolbar">
          <input
            className="toolbar__search"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar por nombre, dirección o tipo…"
            type="search"
            value={search}
          />
          <span className="muted">
            {filtered.length} de {devices.length}
          </span>
          <button
            className="button button--primary"
            onClick={() => setAdding((value) => !value)}
            type="button"
          >
            {adding ? 'Cancelar' : 'Registrar dispositivo'}
          </button>
        </div>

        {adding ? (
          <form className="form-grid" onSubmit={addDevice}>
            <label className="field">
              <span>Nombre</span>
              <input
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                required
                value={form.name}
              />
            </label>
            <label className="field">
              <span>Dirección</span>
              <input
                onChange={(event) => setForm({ ...form, host: event.target.value })}
                placeholder="10.0.0.1"
                required
                value={form.host}
              />
            </label>
            <label className="field">
              <span>Conector</span>
              <select
                onChange={(event) =>
                  setForm({
                    ...form,
                    connector_type: event.target.value as NewDevice['connector_type'],
                  })
                }
                value={form.connector_type}
              >
                <option value="ssh">SSH</option>
                <option value="snmp">SNMP</option>
                <option value="rest">REST</option>
              </select>
            </label>
            <label className="field">
              <span>Tipo</span>
              <select
                onChange={(event) => setForm({ ...form, device_type: event.target.value })}
                value={form.device_type}
              >
                <option value="auto">Detectar</option>
                <option value="mikrotik">MikroTik</option>
                <option value="cisco">Cisco</option>
              </select>
            </label>
            <label className="field">
              <span>Credencial</span>
              <input
                onChange={(event) =>
                  setForm({ ...form, credential_name: event.target.value })
                }
                placeholder="nombre en el vault"
                value={form.credential_name ?? ''}
              />
            </label>
            <label className="field">
              <span>Descripción</span>
              <input
                onChange={(event) => setForm({ ...form, description: event.target.value })}
                value={form.description ?? ''}
              />
            </label>
            <button className="button button--primary" type="submit">
              Guardar
            </button>
          </form>
        ) : null}

        {filtered.length === 0 ? (
          <p className="muted">
            {devices.length === 0
              ? 'Aún no hay dispositivos registrados.'
              : 'Ningún dispositivo coincide con la búsqueda.'}
          </p>
        ) : (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Dirección</th>
                  <th>Conector</th>
                  <th>Estado</th>
                  <th>Última conexión</th>
                  <th aria-label="Acciones" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((device) => (
                  <tr className="row--clickable" key={device.id}>
                    <td>
                      <button
                        className="link"
                        onClick={() => setSelected(device)}
                        type="button"
                      >
                        {device.name}
                      </button>
                      {device.description ? (
                        <div className="muted">{device.description}</div>
                      ) : null}
                    </td>
                    <td>
                      {device.host}:{device.port}
                    </td>
                    <td>{device.connector_type}</td>
                    <td>
                      <span className={`chip chip--status-${device.status}`}>
                        {STATUS_LABEL[device.status]}
                      </span>
                    </td>
                    <td>{device.last_seen ?? '—'}</td>
                    <td className="actions">
                      <button
                        className="button button--secondary"
                        onClick={() => setSelected(device)}
                        type="button"
                      >
                        Ver
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
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
