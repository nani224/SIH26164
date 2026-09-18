import type { Finding, Scan, Policy, RemediationPlanItem, GraphNode, GraphEdge, RiskBands } from '../types/crypto';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export interface FindingsFilterParams {
  band?: string;
  family?: string;
  surface?: string;
  q?: string;
  needsReview?: boolean;
}

// Matches contracts/openapi.yaml's RescoreResult exactly: {bands, changed}.
// changed is the list of Findings whose band or score actually moved -- the
// backend computes this server-side; the frontend must not fabricate a
// "previous" value from the same post-rescore record (see git history for
// why -- that used to make every real, non-mocked rescore show zero change).
export interface RescoreResult {
  bands: RiskBands;
  changed: Finding[];
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API Error ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchScans(): Promise<Scan[]> {
  const res = await fetch(`${API_BASE}/api/v1/scans`);
  return handleResponse<Scan[]>(res);
}

export async function fetchScan(id: string): Promise<Scan> {
  const res = await fetch(`${API_BASE}/api/v1/scans/${id}`);
  return handleResponse<Scan>(res);
}

export async function fetchScanFindings(
  id: string,
  params?: FindingsFilterParams
): Promise<{ items: Finding[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.band && params.band !== 'all') query.set('band', params.band);
  if (params?.family && params.family !== 'all') query.set('family', params.family);
  if (params?.surface && params.surface !== 'all') query.set('surface', params.surface);
  if (params?.q) query.set('q', params.q);
  if (params?.needsReview !== undefined) query.set('needsReview', String(params.needsReview));

  const qs = query.toString();
  const url = `${API_BASE}/api/v1/scans/${id}/findings${qs ? `?${qs}` : ''}`;
  const res = await fetch(url);
  return handleResponse<{ items: Finding[]; total: number }>(res);
}

export async function rescoreScan(
  id: string,
  payload: { crqcYears?: number; policyId?: string }
): Promise<RescoreResult> {
  const res = await fetch(`${API_BASE}/api/v1/scans/${id}/rescore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<RescoreResult>(res);
}

export async function fetchScanGraph(id: string): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
  const res = await fetch(`${API_BASE}/api/v1/scans/${id}/graph`);
  return handleResponse<{ nodes: GraphNode[]; edges: GraphEdge[] }>(res);
}

export async function fetchScanCbom(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/scans/${id}/cbom`);
  return handleResponse<any>(res);
}

export async function fetchScanPlan(id: string): Promise<RemediationPlanItem[]> {
  const res = await fetch(`${API_BASE}/api/v1/scans/${id}/plan`);
  const data = await handleResponse<{ scanId: string; generatedAt: string; items: RemediationPlanItem[] }>(res);
  return data.items;
}

export async function fetchPolicies(): Promise<Policy[]> {
  const res = await fetch(`${API_BASE}/api/v1/policies`);
  return handleResponse<Policy[]>(res);
}

export async function fetchPolicy(id: string): Promise<Policy> {
  const res = await fetch(`${API_BASE}/api/v1/policies/${id}`);
  return handleResponse<Policy>(res);
}

export async function updatePolicy(id: string, policy: Policy): Promise<Policy> {
  const res = await fetch(`${API_BASE}/api/v1/policies/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(policy),
  });
  return handleResponse<Policy>(res);
}

export async function createPolicy(policy: Policy): Promise<Policy> {
  const res = await fetch(`${API_BASE}/api/v1/policies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(policy),
  });
  return handleResponse<Policy>(res);
}

export async function createScan(
  data: { path?: string; policyId?: string; crqcYears?: number } | FormData
): Promise<Scan> {
  let options: RequestInit = { method: 'POST' };
  let url = `${API_BASE}/api/v1/scans`;
  if (typeof FormData !== 'undefined' && data instanceof FormData) {
    url = `${API_BASE}/api/v1/scans/upload`;
    options.body = data;
  } else {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(data);
  }
  const res = await fetch(url, options);
  return handleResponse<Scan>(res);
}

export async function triageFinding(
  id: string,
  payload: { status: Finding['triage']['status']; note?: string }
): Promise<Finding> {
  const res = await fetch(`${API_BASE}/api/v1/findings/${id}/triage`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<Finding>(res);
}
