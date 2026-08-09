/**
 * Client for the Lynjax API.
 *
 * Requests are relative by default because FastAPI serves this bundle from the
 * same origin, so there is no cross-origin setup to keep in sync and nothing to
 * configure at deploy time. `VITE_LYNJAX_API_BASE_URL` exists only for `npm run
 * dev`, where Vite serves on a different port.
 */

const API_BASE_URL = import.meta.env.VITE_LYNJAX_API_BASE_URL ?? '';

const TOKEN_KEY = 'lynjax.token';

/**
 * Session token storage.
 *
 * sessionStorage, not localStorage: a field laptop is often shared, and a token
 * that survives closing the browser is one more thing to remember to clear.
 */
export const session = {
  get token(): string | null {
    return sessionStorage.getItem(TOKEN_KEY);
  },
  set(token: string) {
    sessionStorage.setItem(TOKEN_KEY, token);
  },
  clear() {
    sessionStorage.removeItem(TOKEN_KEY);
  },
};

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }

  /**
   * True when the server refused because real network access is disabled.
   * Distinct from a fault: the UI should explain the switch, not show an error.
   */
  get isPolicyRefusal(): boolean {
    return this.status === 403 && /LYNJAX_NETWORK_POLICY|authorized-targets/.test(this.message);
  }

  /** The caller is signed in but lacks the role for this action. */
  get isForbidden(): boolean {
    return this.status === 403 && !this.isPolicyRefusal;
  }

  get isUnauthenticated(): boolean {
    return this.status === 401;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    const token = session.token;
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    });
  } catch (cause) {
    throw new ApiError(0, `No se pudo contactar la API: ${String(cause)}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const body = await response.json().catch(() => null);

  if (response.status === 401) {
    // The token expired or the account changed. Drop it so the app returns to
    // the sign-in screen rather than retrying with something already rejected.
    session.clear();
  }

  if (!response.ok) {
    // FastAPI puts the message in `detail`, and for validation errors that is
    // a list of objects rather than a string.
    const detail = body?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((item: { msg?: string }) => item.msg ?? '').join('; ')
          : `HTTP ${response.status}`;
    throw new ApiError(response.status, message);
  }

  return body as T;
}

// ─── Types ───

export type Device = {
  id: number;
  name: string;
  host: string;
  port: number;
  connector_type: string;
  device_type: string;
  credential_name: string | null;
  description: string | null;
  is_active: boolean;
  status: 'online' | 'offline' | 'warning' | 'unknown';
  last_seen: string | null;
};

export type NewDevice = {
  name: string;
  host: string;
  connector_type: 'ssh' | 'snmp' | 'rest';
  device_type?: string;
  port?: number | null;
  credential_name?: string | null;
  description?: string | null;
};

export type ConnectivityCheck = {
  device_id: number;
  device_name: string;
  host: string;
  reachable: boolean;
  latency_ms: number | null;
  error: string | null;
};

export type Finding = {
  name: string;
  status: 'pass' | 'warning' | 'fail';
  message: string;
  details?: Record<string, unknown> | null;
};

export type ChainHop = {
  role: 'endpoint' | 'access' | 'transit' | 'edge' | 'unknown';
  name: string;
  host: string;
  device_id: number | null;
  port: string | null;
  evidence: string;
  findings: Finding[];
};

export type ChainTrace = {
  target: string;
  resolved_mac: string;
  verdict: 'pass' | 'warning' | 'fail';
  summary: string;
  hops: ChainHop[];
  findings: Finding[];
};

export type AuditResult = {
  assessment_id: string;
  client: string;
  started_at: string;
  verdict: 'pass' | 'warning' | 'fail';
  summary: string;
  devices_assessed: number;
  unreachable: { device: string; reason: string }[];
  findings: Finding[];
  trace: ChainTrace | null;
  report_url: string;
};

export type DiscoveredHost = {
  ip: string;
  hostname: string;
  open_ports: number[];
  device_hint: string;
  banner: string;
  already_registered: boolean;
};

export type DiscoveryJob = {
  job_id: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  networks: string[];
  methods: string[];
  total_hosts: number;
  scanned_hosts: number;
  responding_hosts: number;
  progress_percent: number;
  started_at: string;
  completed_at: string | null;
  error: string | null;
  results: DiscoveredHost[];
};

export type SystemInfo = {
  name: string;
  version: string;
  environment: string;
  network_policy: 'simulated-checks-only' | 'authorized-targets';
};

// ─── Calls ───

export type Account = {
  id: number;
  email: string;
  role: 'admin' | 'operator' | 'viewer';
  is_active: boolean;
  full_name: string | null;
};

export type LoginResult = {
  access_token: string;
  email: string;
  role: Account['role'];
};

export const api = {
  info: () => request<SystemInfo>('/api/v1/info'),

  login: async (email: string, password: string): Promise<LoginResult> => {
    const result = await request<LoginResult>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    session.set(result.access_token);
    return result;
  },

  me: () => request<Account>('/api/v1/auth/me'),

  logout: () => session.clear(),

  listDevices: () => request<Device[]>('/api/v1/devices'),

  createDevice: (device: NewDevice) =>
    request<Device>('/api/v1/devices', {
      method: 'POST',
      body: JSON.stringify(device),
    }),

  deleteDevice: (id: number) =>
    request<void>(`/api/v1/devices/${id}`, { method: 'DELETE' }),

  checkDevice: (id: number) =>
    request<ConnectivityCheck>(`/api/v1/devices/${id}/check`, { method: 'POST' }),

  runAudit: (payload: { client?: string; trace_target?: string; locale?: string }) =>
    request<AuditResult>('/api/v1/audit', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  trace: (targetIp: string) =>
    request<ChainTrace>(`/api/v1/trace/${encodeURIComponent(targetIp)}`, {
      method: 'POST',
    }),

  startDiscovery: (payload: {
    subnets: string[];
    methods?: string[];
    max_hosts?: number;
    allow_public?: boolean;
    snmp_community?: string;
  }) =>
    request<DiscoveryJob>('/api/v1/discovery', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getDiscoveryJob: (jobId: string) =>
    request<DiscoveryJob>(`/api/v1/discovery/${jobId}`),

  /**
   * Download a report.
   *
   * Fetched rather than linked: an <a href> carries no Authorization header, so
   * a plain link would 401 now that reports require a session.
   */
  downloadReport: async (assessmentId: string, format: 'md' | 'pdf') => {
    const token = session.token;
    const response = await fetch(
      `${API_BASE_URL}/api/v1/reports/${assessmentId}?fmt=${format}`,
      { headers: token ? { Authorization: `Bearer ${token}` } : {} },
    );

    if (!response.ok) {
      throw new ApiError(response.status, `No se pudo descargar el informe.`);
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${assessmentId}.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};

export { API_BASE_URL };
