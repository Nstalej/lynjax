import type { ConnectivityAssessmentResponse } from '../types/platform';

const API_BASE_URL = import.meta.env.VITE_LYNJAX_API_BASE_URL ?? 'http://127.0.0.1:8000';

type ConnectivityDemoRequest = {
  hosts: string[];
  checks: string[];
};

export async function runConnectivityDemoAssessment(
  payload: ConnectivityDemoRequest = {
    hosts: ['target-web', 'target-metadata'],
    checks: ['http', 'dns'],
  },
): Promise<ConnectivityAssessmentResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/assessments/connectivity-demo`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Connectivity demo failed with HTTP ${response.status}`);
  }

  return response.json() as Promise<ConnectivityAssessmentResponse>;
}

export { API_BASE_URL };
