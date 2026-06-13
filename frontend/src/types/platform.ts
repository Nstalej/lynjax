export type StatusTone = 'stable' | 'watch' | 'alert' | 'neutral';

export type ModuleStatus = 'active' | 'ready' | 'planned' | 'readonly';

export type PlatformMetric = {
  id: string;
  label: string;
  value: string;
  detail: string;
  tone: StatusTone;
  status: string;
};

export type ModuleInsight = {
  id: string;
  title: string;
  body: string;
  status: ModuleStatus;
  metadata?: string;
};

export type AssetRecord = {
  id: string;
  name: string;
  kind: string;
  zone: string;
  status: 'observed' | 'needs-review' | 'planned';
};

export type EvidenceRecord = {
  id: string;
  title: string;
  source: string;
  retention: string;
  status: 'linked' | 'simulated' | 'pending';
};

export type AssessmentEvidenceSummary = {
  items_collected: number;
  collection_mode: string;
  storage: string;
};

export type StructuredCheckResult = {
  name: string;
  status: string;
  summary: string;
};

export type AssessmentTargetResult = {
  target: string;
  status: string;
  checks: StructuredCheckResult[];
};

export type ConnectivityAssessmentResponse = {
  assessment_id: string;
  created_at: string;
  mode: string;
  network_access: string;
  targets: string[];
  checks: string[];
  results: AssessmentTargetResult[];
  evidence_summary: AssessmentEvidenceSummary;
  overall_status: string;
  risk_level: string;
  safety_notice: string;
  report_markdown: string;
};
