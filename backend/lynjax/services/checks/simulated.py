from lynjax.schemas.assessments import AssessmentTargetResult, StructuredCheckResult


def build_simulated_connectivity_results(
    hosts: list[str], checks: list[str]
) -> list[AssessmentTargetResult]:
    """Return deterministic demo results without opening sockets or scanning networks."""
    return [
        AssessmentTargetResult(
            target=host,
            status="simulated-pass",
            checks=[
                StructuredCheckResult(
                    name=check,
                    status="simulated-pass",
                    summary=f"{check} check simulated successfully for {host}",
                )
                for check in checks
            ],
        )
        for host in hosts
    ]
