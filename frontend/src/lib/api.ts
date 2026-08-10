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

export type DashboardSummary = {
  devices: {
    total: number;
    active: number;
    by_status: Record<'online' | 'offline' | 'warning' | 'unknown', number>;
  };
  health_score: number | null;
  health_basis: string;
  agents: { total: number; online: number };
  audits: {
    by_verdict: Record<string, number>;
    recent: {
      assessment_id: string;
      target: string;
      audit_type: string;
      verdict: string;
      issues_total: number;
      started_at: string;
    }[];
  };
  network_policy: string;
};

export type TopologyNode = {
  id: string;
  label: string;
  kind: 'device' | 'endpoint' | 'gateway' | 'unmanaged';
  status: string;
  detail: Record<string, unknown>;
};

export type TopologyEdge = {
  source: string;
  target: string;
  evidence: string;
  label: string;
};

export type Topology = {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  notes: string[];
};

export type InterfaceRow = {
  name: string;
  status: string;
  speed: number | null;
  mac: string | null;
  ip: string | null;
  rx_bytes: number;
  tx_bytes: number;
  errors: number;
};

export type ArpRow = { ip: string; mac: string; interface: string; type: string };
export type MacRow = { mac: string; port: string; vlan: number; type: string };
export type RouteRow = {
  destination: string;
  gateway: string;
  interface: string;
  metric: number;
  protocol: string;
};

export type DeviceData = {
  device: {
    id: number;
    name: string;
    host: string;
    connector_type: string;
    device_type: string;
  };
  error: string | null;
  collected: boolean;
  system: Record<string, string>;
  interfaces: InterfaceRow[];
  arp: ArpRow[];
  mac: MacRow[];
  routes: RouteRow[];
};

export type AuditRecord = {
  id: number;
  assessment_id: string;
  client: string | null;
  target: string;
  audit_type: string;
  status: string;
  verdict: 'pass' | 'warning' | 'fail';
  checks_total: number;
  issues_total: number;
  summary: string | null;
  started_at: string;
  completed_at: string | null;
};

export type StoredAudit = AuditRecord & { payload: AuditResult };

export type AgentRecord = {
  id: number;
  agent_id: string;
  name: string;
  host: string;
  agent_type: string;
  version: string | null;
  status: 'online' | 'offline' | 'unknown';
  last_heartbeat: string | null;
  registered_at: string;
};

export type CredentialRecord = {
  id: number;
  name: string;
  type: string;
  created_at: string;
  updated_at: string | null;
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

  dashboard: () => request<DashboardSummary>('/api/v1/dashboard'),

  topology: () => request<Topology>('/api/v1/topology'),

  listDevices: () => request<Device[]>('/api/v1/devices'),

  deviceData: (id: number) => request<DeviceData>(`/api/v1/devices/${id}/data`),

  auditDevice: (id: number) =>
    request<{ checks: Finding[]; overall_status: string; summary: string }>(
      `/api/v1/devices/${id}/audit`,
      { method: 'POST' },
    ),

  listAudits: (params: { audit_type?: string; verdict?: string } = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, value]) => Boolean(value)) as [string, string][],
    ).toString();
    return request<AuditRecord[]>(`/api/v1/audits${query ? `?${query}` : ''}`);
  },

  getAudit: (id: number) => request<StoredAudit>(`/api/v1/audits/${id}`),

  listAgents: () => request<AgentRecord[]>('/api/v1/agents'),

  deleteAgent: (agentId: string) =>
    request<void>(`/api/v1/agents/${agentId}`, { method: 'DELETE' }),

  listCredentials: () => request<CredentialRecord[]>('/api/v1/credentials'),

  createCredential: (payload: { name: string; type: string; data: Record<string, unknown> }) =>
    request<{ id: number }>('/api/v1/credentials', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  deleteCredential: (name: string) =>
    request<void>(`/api/v1/credentials/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    }),

  logs: (lines = 300) =>
    request<{ path: string; lines: string[]; note: string | null }>(
      `/api/v1/logs?lines=${lines}`,
    ),

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
