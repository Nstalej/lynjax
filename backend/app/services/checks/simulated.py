from app.schemas.assessments import HostConnectivityResult, SimulatedCheckResult


def build_simulated_connectivity_results(
    hosts: list[str], checks: list[str]
) -> list[HostConnectivityResult]:
    """Return deterministic demo results without opening sockets or scanning networks."""
    return [
        HostConnectivityResult(
            host=host,
            checks=[
                SimulatedCheckResult(name=check, status="simulated-pass")
                for check in checks
            ],
        )
        for host in hosts
    ]
