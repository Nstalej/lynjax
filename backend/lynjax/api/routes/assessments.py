from fastapi import APIRouter

from lynjax.schemas.assessments import (
    AssessmentEvidenceSummary,
    ConnectivityAssessmentRequest,
    ConnectivityAssessmentResponse,
)
from lynjax.services.checks import build_simulated_connectivity_results
from lynjax.services.reports.markdown import render_connectivity_assessment_report

router = APIRouter(prefix="/api/v1/assessments")

SAFETY_NOTICE = (
    "Demo/local assessment only. No sockets are opened, no external networks are scanned, "
    "and no credentials are used."
)


@router.post("/connectivity-demo", response_model=ConnectivityAssessmentResponse)
def connectivity_demo(
    request: ConnectivityAssessmentRequest,
) -> ConnectivityAssessmentResponse:
    results = build_simulated_connectivity_results(request.hosts, request.checks)
    response = ConnectivityAssessmentResponse(
        assessment_id=f"demo-connectivity-{'-'.join(request.hosts)}",
        created_at="2026-06-13T00:00:00Z",
        mode="simulation",
        network_access="disabled",
        targets=request.hosts,
        checks=request.checks,
        results=results,
        evidence_summary=AssessmentEvidenceSummary(
            items_collected=len(request.hosts) * len(request.checks),
            collection_mode="simulated",
            storage="response-only",
        ),
        overall_status="completed",
        risk_level="low",
        safety_notice=SAFETY_NOTICE,
        report_markdown="",
    )
    response.report_markdown = render_connectivity_assessment_report(response)
    return response
