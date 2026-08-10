import { useCallback, useEffect, useState } from 'react';
import { PolicyNotice } from '../components/PolicyNotice';
import {
  ApiError,
  api,
  type Account,
  type CredentialRecord,
  type SystemInfo,
} from '../lib/api';

const SECTIONS = [
  { id: 'general', label: 'General' },
  { id: 'credentials', label: 'Credenciales' },
  { id: 'logs', label: 'Registro' },
] as const;

type SectionId = (typeof SECTIONS)[number]['id'];

const CREDENTIAL_TYPES = [
  { value: 'ssh', label: 'SSH' },
  { value: 'snmp', label: 'SNMP v2c' },
  { value: 'snmpv3', label: 'SNMP v3' },
  { value: 'rest', label: 'REST / API' },
];

export function SettingsPage({ account }: { account: Account }) {
  const [section, setSection] = useState<SectionId>('general');
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [credentials, setCredentials] = useState<CredentialRecord[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [logPath, setLogPath] = useState('');
  const [error, setError] = useState<ApiError | null>(null);

  const [name, setName] = useState('');
  const [type, setType] = useState('ssh');
  const [username, setUsername] = useState('');
  const [secret, setSecret] = useState('');

  const load = useCallback(async () => {
    try {
      setInfo(await api.info());
      if (account.role !== 'viewer') {
        setCredentials(await api.listCredentials());
      }
      setError(null);
    } catch (cause) {
      setError(cause as ApiError);
    }
  }, [account.role]);

  useEffect(() => {
    void load();
  }, [load]);

  const loadLogs = useCallback(async () => {
    try {
      const body = await api.logs();
      setLogs(body.lines);
      setLogPath(body.path);
      setError(null);
    } catch (cause) {
      setError(cause as ApiError);
    }
  }, []);

  useEffect(() => {
    if (section === 'logs') void loadLogs();
  }, [section, loadLogs]);

  async function addCredential(event: React.FormEvent) {
    event.preventDefault();
    // The field means different things per type; SNMP v2c has a community, not
    // a username, and sending the wrong key would store a credential that
    // silently fails at connection time.
    const data =
      type === 'snmp'
        ? { version: 'v2c', community: secret || username }
        : type === 'snmpv3'
          ? { version: 'v3', username, auth_key: secret, priv_key: secret }
          : { username, password: secret };

    try {
      await api.createCredential({ name, type: type === 'snmpv3' ? 'snmp' : type, data });
      setName('');
      setUsername('');
      setSecret('');
      setCredentials(await api.listCredentials());
      setError(null);
    } catch (cause) {
      setError(cause as ApiError);
    }
  }

  async function removeCredential(credential: CredentialRecord) {
    try {
      await api.deleteCredential(credential.name);
      setCredentials(await api.listCredentials());
    } catch (cause) {
      setError(cause as ApiError);
    }
  }

  return (
    <div className="settings">
      <aside className="settings__nav">
        {SECTIONS.map((item) => (
          <button
            className={`nav-item ${section === item.id ? 'nav-item--active' : ''}`}
            key={item.id}
            onClick={() => setSection(item.id)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </aside>

      <div className="settings__body">
        {error ? <PolicyNotice error={error} /> : null}

        {section === 'general' && info ? (
          <section className="panel">
            <h2>Configuración</h2>
            <dl className="facts">
              <div>
                <dt>Aplicación</dt>
                <dd>
                  {info.name} {info.version}
                </dd>
              </div>
              <div>
                <dt>Entorno</dt>
                <dd>{info.environment}</dd>
              </div>
              <div>
                <dt>Política de red</dt>
                <dd>
                  <span
                    className={`chip chip--${
                      info.network_policy === 'authorized-targets' ? 'warning' : 'pass'
                    }`}
                  >
                    {info.network_policy}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Sesión</dt>
                <dd>
                  {account.email} · {account.role}
                </dd>
              </div>
            </dl>

            <p className="muted">
              La política de red y las rutas de datos se definen con variables de
              entorno, no desde aquí: un interruptor en la interfaz para habilitar el
              acceso real a la red sería demasiado fácil de accionar por accidente.
            </p>
          </section>
        ) : null}

        {section === 'credentials' ? (
          <section className="panel">
            <h2>Credenciales</h2>
            <p className="muted">
              Se guardan cifradas. El listado nunca devuelve el secreto, solo su
              nombre y tipo.
            </p>

            <form className="form-grid" onSubmit={addCredential}>
              <label className="field">
                <span>Identificador</span>
                <input
                  onChange={(event) => setName(event.target.value)}
                  placeholder="switches-core-ssh"
                  required
                  value={name}
                />
              </label>
              <label className="field">
                <span>Tipo</span>
                <select onChange={(event) => setType(event.target.value)} value={type}>
                  {CREDENTIAL_TYPES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>{type === 'snmp' ? 'Comunidad' : 'Usuario'}</span>
                <input
                  onChange={(event) => setUsername(event.target.value)}
                  value={username}
                />
              </label>
              <label className="field">
                <span>{type === 'snmp' ? 'Comunidad (secreta)' : 'Contraseña'}</span>
                <input
                  onChange={(event) => setSecret(event.target.value)}
                  type="password"
                  value={secret}
                />
              </label>
              <button className="button button--primary" type="submit">
                Cifrar y guardar
              </button>
            </form>

            {credentials.length === 0 ? (
              <p className="muted">Sin credenciales guardadas.</p>
            ) : (
              <div className="table-scroll">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Identificador</th>
                      <th>Tipo</th>
                      <th>Creada</th>
                      <th aria-label="Acciones" />
                    </tr>
                  </thead>
                  <tbody>
                    {credentials.map((credential) => (
                      <tr key={credential.id}>
                        <td>{credential.name}</td>
                        <td>{credential.type}</td>
                        <td>{credential.created_at}</td>
                        <td className="actions">
                          <button
                            className="button button--ghost"
                            onClick={() => void removeCredential(credential)}
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
        ) : null}

        {section === 'logs' ? (
          <section className="panel">
            <div className="panel__head">
              <h2>Registro del sistema</h2>
              <button
                className="button button--secondary"
                onClick={() => void loadLogs()}
                type="button"
              >
                Actualizar
              </button>
            </div>
            <p className="muted">{logPath}</p>
            <pre className="logs">
              {logs.length === 0 ? 'Sin entradas todavía.' : logs.join('\n')}
            </pre>
          </section>
        ) : null}
      </div>
    </div>
  );
}
