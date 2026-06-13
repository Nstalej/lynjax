from pydantic import BaseModel, Field


class InfoResponse(BaseModel):
    name: str
    version: str
    environment: str
    network_policy: str


class ConnectivityAssessmentRequest(BaseModel):
    hosts: list[str] = Field(..., min_length=1, max_length=20)
    checks: list[str] = Field(default_factory=lambda: ["http"], min_length=1, max_length=10)


class StructuredCheckResult(BaseModel):
    name: str
    status: str
    summary: str


class AssessmentTargetResult(BaseModel):
    target: str
    status: str
    checks: list[StructuredCheckResult]


class AssessmentEvidenceSummary(BaseModel):
    items_collected: int
    collection_mode: str
    storage: str


class ConnectivityAssessmentResponse(BaseModel):
    assessment_id: str
    created_at: str
    mode: str
    network_access: str
    targets: list[str]
    checks: list[str]
    results: list[AssessmentTargetResult]
    evidence_summary: AssessmentEvidenceSummary
    overall_status: str
    risk_level: str
    safety_notice: str
    report_markdown: str
