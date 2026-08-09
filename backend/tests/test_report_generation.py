from lynjax.schemas.assessments import (
    AssessmentEvidenceSummary,
    AssessmentTargetResult,
    ConnectivityAssessmentResponse,
    StructuredCheckResult,
)
from lynjax.services.reports.markdown import render_connectivity_assessment_report


def test_markdown_renderer_uses_structured_assessment_data():
    response = ConnectivityAssessmentResponse(
        assessment_id="demo-connectivity-target-web",
        created_at="2026-06-13T00:00:00Z",
        mode="simulation",
        network_access="disabled",
        targets=["target-web"],
        checks=["http"],
        results=[
            AssessmentTargetResult(
                target="target-web",
                status="simulated-pass",
                checks=[
                    StructuredCheckResult(
                        name="http",
                        status="simulated-pass",
                        summary="http check simulated successfully for target-web",
                    )
                ],
            )
        ],
        evidence_summary=AssessmentEvidenceSummary(
            items_collected=1,
            collection_mode="simulated",
            storage="response-only",
        ),
        overall_status="completed",
        risk_level="low",
        safety_notice="Demo/local assessment only.",
        report_markdown="",
    )

    markdown = render_connectivity_assessment_report(response)

    assert "# Lynjax Connectivity Demo Assessment" in markdown
    assert "Assessment ID: demo-connectivity-target-web" in markdown
    assert "- **Targets:** target-web" in markdown
    assert (
        "| target-web | http | simulated-pass | http check simulated successfully for target-web |"
        in markdown
    )
    assert "Demo/local assessment only." in markdown
