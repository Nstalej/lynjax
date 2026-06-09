from fastapi import APIRouter

from app.schemas.assessments import (
    ConnectivityAssessmentRequest,
    ConnectivityAssessmentResponse,
)
from app.services.checks import build_simulated_connectivity_results

router = APIRouter(prefix="/api/v1/assessments")


@router.post("/connectivity-demo", response_model=ConnectivityAssessmentResponse)
def connectivity_demo(
    request: ConnectivityAssessmentRequest,
) -> ConnectivityAssessmentResponse:
    return ConnectivityAssessmentResponse(
        mode="simulation",
        network_access="disabled",
        results=build_simulated_connectivity_results(request.hosts, request.checks),
    )
