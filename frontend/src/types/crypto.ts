import type { components, paths } from './api.generated';

export type Schemas = components['schemas'];
export type Finding = Schemas['Finding'];
export type Scan = Schemas['Scan'];
export type ScanStats = Schemas['ScanStats'];
export type RiskBand = Schemas['RiskBand'];
// Contract names these BandCounts/Context/ContextWithGlob/PqcCatalogEntry;
// keep the frontend's own names as aliases so call sites don't churn.
export type RiskBands = Schemas['BandCounts'];
export type Policy = Schemas['Policy'];
export type PolicyContext = Schemas['Context'];
export type PolicyRule = Schemas['ContextWithGlob'];
export type RemediationPlanItem = Schemas['RemediationPlanItem'];
export type GraphNode = Schemas['GraphNode'];
export type GraphEdge = Schemas['GraphEdge'];
export type PqcCatalogItem = Schemas['PqcCatalogEntry'];

// v0.3.0 Continuous Operation Schemas
export type Target = Schemas['Target'];
export type TargetKind = Schemas['TargetKind'];
export type TargetCreate = Schemas['TargetCreate'];
export type TargetPatch = Schemas['TargetPatch'];
export type EstateSummary = Schemas['EstateSummary'];
export type EstateTrend = Schemas['EstateTrend'];
export type EstateTrendPoint = Schemas['EstateTrendPoint'];
export type ScanSnapshot = Schemas['ScanSnapshot'];
export type Drift = Schemas['Drift'];
export type DriftChangedItem = Schemas['DriftChangedItem'];
export type DriftSummary = Schemas['DriftSummary'];
export type Alert = Schemas['Alert'];
export type AlertType = Schemas['AlertType'];
export type ProbeResult = Omit<Schemas['ProbeResult'], 'negotiated' | 'supported'> & {
  negotiated: Record<string, any>;
  supported: Record<string, any>[];
};
export type ProbeProtocol = Schemas['ProbeProtocol'];
export type HsmInventory = Schemas['HsmInventory'];
export type HsmSlot = Schemas['HsmSlot'];
export type HsmKey = Schemas['HsmKey'];
export type AuditVerifyResponse = Schemas['AuditVerifyResponse'];

/**
 * Strict Cryptographic Semantic Classes (Prompt 1, Section 7)
 * Identical across every chart, badge, node, and border.
 */
export type CryptoSemanticClass =
  | 'shor' // Shor-vulnerable (RSA, ECC, DH) -> Ember Red
  | 'classically-broken' // Classically broken today (MD5, SHA-1, DES, RC4, ECB) -> Magenta-Violet + Hatch Pattern
  | 'grover' // Grover-weakened (AES-128) -> Amber
  | 'quantum-safe-classical' // Quantum-safe classical (AES-256, SHA-2/3) -> Steel Blue
  | 'pqc'; // Post-quantum (ML-KEM, ML-DSA, SLH-DSA) -> Lattice Teal

export function classifyAlgorithm(family: string | null, displayName: string, classicallyBroken?: boolean): CryptoSemanticClass {
  const norm = ((family ?? '') + ' ' + displayName).toUpperCase();
  if (classicallyBroken || norm.includes('MD5') || norm.includes('SHA-1') || norm.includes('SHA1') || norm.includes('DES') || norm.includes('RC4') || norm.includes('ECB')) {
    return 'classically-broken';
  }
  if (norm.includes('RSA') || norm.includes('ECC') || norm.includes('ECDSA') || norm.includes('ECDH') || norm.includes('ED25519') || norm.includes('X25519') || norm.includes('DH')) {
    return 'shor';
  }
  if (norm.includes('ML-KEM') || norm.includes('ML-DSA') || norm.includes('SLH-DSA') || norm.includes('FALCON') || norm.includes('SNTRUP')) {
    return 'pqc';
  }
  if (norm.includes('AES-128') || norm.includes('128-BIT') || norm.includes('CHACHA20')) {
    return 'grover';
  }
  if (norm.includes('AES-256') || norm.includes('SHA-256') || norm.includes('SHA-384') || norm.includes('SHA-512') || norm.includes('SHA3')) {
    return 'quantum-safe-classical';
  }
  return 'shor';
}
