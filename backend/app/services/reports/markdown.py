from app.schemas.assessments import ConnectivityAssessmentResponse


def render_connectivity_assessment_report(
    response: ConnectivityAssessmentResponse,
) -> str:
    """Render a deterministic Markdown report from structured assessment data."""
    lines = [
        "# Lynjax Connectivity Demo Assessment",
        "",
        f"Assessment ID: {response.assessment_id}",
        f"Created at: {response.created_at}",
        f"Mode: {response.mode}",
        f"Network access: {response.network_access}",
        "",
        "## Scope",
        "",
        f"- **Targets:** {', '.join(response.targets)}",
        f"- **Checks:** {', '.join(response.checks)}",
        f"- **Overall status:** {response.overall_status}",
        f"- **Risk level:** {response.risk_level}",
        "",
        "## Results",
        "",
        "| Target | Check | Status | Summary |",
        "| --- | --- | --- | --- |",
    ]

    for target_result in response.results:
        for check in target_result.checks:
            lines.append(
                f"| {target_result.target} | {check.name} | {check.status} | {check.summary} |"
            )

    lines.extend(
        [
            "",
            "## Evidence Summary",
            "",
            f"- Items collected: {response.evidence_summary.items_collected}",
            f"- Collection mode: {response.evidence_summary.collection_mode}",
            f"- Storage: {response.evidence_summary.storage}",
            "",
            "## Safety Notice",
            "",
            response.safety_notice,
            "",
        ]
    )

    return "\n".join(lines)
