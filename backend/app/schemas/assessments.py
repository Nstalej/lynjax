from pydantic import BaseModel, Field


class InfoResponse(BaseModel):
    name: str
    version: str
    environment: str
    network_policy: str


class ConnectivityAssessmentRequest(BaseModel):
    hosts: list[str] = Field(..., min_length=1, max_length=20)
    checks: list[str] = Field(default_factory=lambda: ["http"], min_length=1, max_length=10)


class SimulatedCheckResult(BaseModel):
    name: str
    status: str


class HostConnectivityResult(BaseModel):
    host: str
    checks: list[SimulatedCheckResult]


class ConnectivityAssessmentResponse(BaseModel):
    mode: str
    network_access: str
    results: list[HostConnectivityResult]
