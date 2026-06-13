import type { AssetRecord, EvidenceRecord, ModuleInsight, PlatformMetric } from '../types/platform';

export const platformMetrics: PlatformMetric[] = [
  {
    id: 'assets',
    label: 'Activos visibles',
    value: '23',
    detail: 'Inventario sanitizado de laboratorio.',
    tone: 'stable',
    status: 'Operativo',
  },
  {
    id: 'findings',
    label: 'Hallazgos priorizados',
    value: '7',
    detail: 'Muestras de riesgo pendientes de validación.',
    tone: 'watch',
    status: 'Observación',
  },
  {
    id: 'evidence',
    label: 'Evidencias vinculadas',
    value: '12',
    detail: 'Artefactos listos para reporte.',
    tone: 'stable',
    status: 'Trazable',
  },
  {
    id: 'risk',
    label: 'Riesgo crítico',
    value: '1',
    detail: 'Solo como visual de priorización.',
    tone: 'alert',
    status: 'Demo',
  },
];

export const assets: AssetRecord[] = [
  { id: 'asset-1', name: 'lynx-core-fw', kind: 'Firewall virtual', zone: 'Lab edge', status: 'observed' },
  { id: 'asset-2', name: 'target-web', kind: 'Servicio HTTP demo', zone: 'Sandbox', status: 'observed' },
  { id: 'asset-3', name: 'target-metadata', kind: 'Nodo simulado', zone: 'Sandbox', status: 'needs-review' },
  { id: 'asset-4', name: 'ad-placeholder', kind: 'Directorio futuro', zone: 'Read-only', status: 'planned' },
];

export const evidenceRecords: EvidenceRecord[] = [
  { id: 'ev-1', title: 'Connectivity demo response', source: 'POST /api/v1/assessments/connectivity-demo', retention: 'response-only', status: 'simulated' },
  { id: 'ev-2', title: 'Markdown assessment report', source: 'Backend renderer', retention: 'copy/export preview', status: 'linked' },
  { id: 'ev-3', title: 'Lab topology snapshot', source: 'Day 4 virtual lab prep', retention: 'pending artifact', status: 'pending' },
];

export const moduleInsights: Record<string, ModuleInsight[]> = {
  connectivity: [
    { id: 'conn-1', title: 'Checks permitidos', body: 'HTTP y DNS simulados contra targets locales de demo.', status: 'ready', metadata: 'Sin sockets reales' },
    { id: 'conn-2', title: 'Política de red', body: 'El backend devuelve network_access=disabled para impedir confusión con escaneo real.', status: 'ready', metadata: 'localhost only' },
  ],
  assessments: [
    { id: 'assess-1', title: 'Contrato v1.0', body: 'assessment_id, targets, checks, results, evidence_summary y report_markdown.', status: 'ready', metadata: 'FastAPI/Pydantic' },
    { id: 'assess-2', title: 'Próximo paso', body: 'Persistencia/export solo después de validar el flujo local.', status: 'planned', metadata: 'Day 5' },
  ],
  reports: [
    { id: 'report-1', title: 'Markdown técnico', body: 'El backend renderiza un reporte desde la misma respuesta estructurada.', status: 'ready', metadata: 'copy-ready' },
    { id: 'report-2', title: 'PDF/manual', body: 'Preparado para empaquetado v1.0-rc1 cuando exista toolchain.', status: 'planned', metadata: 'release track' },
  ],
  topology: [
    { id: 'topo-1', title: 'Mapa manual', body: 'Nodos sanitizados para guiar el laboratorio virtual.', status: 'planned', metadata: 'no discovery' },
    { id: 'topo-2', title: 'Containerlab futuro', body: 'La topología se validará como artifact YAML, no se ejecutará en Windows sin aprobación.', status: 'planned', metadata: 'Day 4' },
  ],
  directory: [
    { id: 'dir-1', title: 'Modelo AD', body: 'Usuarios, grupos, equipos y GPOs se mostrarán primero como datos de muestra.', status: 'readonly', metadata: 'sin credenciales' },
    { id: 'dir-2', title: 'Agentes deshabilitados', body: 'No hay bind LDAP, WinRM ni recolección de dominio en este candidato.', status: 'readonly', metadata: 'future milestone' },
  ],
  intelligence: [
    { id: 'llm-1', title: 'Análisis read-only', body: 'Placeholder para resumen de reportes con minimización de datos.', status: 'readonly', metadata: 'sin MCP activo' },
    { id: 'llm-2', title: 'Acciones bloqueadas', body: 'Cualquier acción LLM/MCP futura requerirá aprobación humana y auditoría.', status: 'readonly', metadata: 'guardrails' },
  ],
};
