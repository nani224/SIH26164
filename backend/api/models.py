"""Pydantic v2 models mirroring the schemas in contracts/openapi.yaml.

These are the Phase 0 contract types. Nothing here is wired to a real
detection engine yet (that is Phase 1+) — the API layer only ever
constructs these from the in-memory stub data in stub_data.py.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

# StrEnum (not Literal) deliberately: Pydantic/FastAPI emits these as named
# `components.schemas` entries matching contracts/openapi.yaml, which a
# plain Literal would inline instead -- see docs/decisions/backend/001.


class FindingKind(StrEnum):
    ALGORITHM = "algorithm"
    CERTIFICATE = "certificate"
    KEY = "key"
    PROTOCOL = "protocol"
    LIBRARY = "library"


class Surface(StrEnum):
    SOURCE = "source"
    BINARY = "binary"
    CERTIFICATE = "certificate"
    CONFIG = "config"
    IMAGE = "image"
    MANIFEST = "manifest"


class Family(StrEnum):
    RSA = "RSA"
    DSA = "DSA"
    DH = "DH"
    ECDH = "ECDH"
    ECDSA = "ECDSA"
    ED25519 = "Ed25519"
    X25519 = "X25519"
    AES = "AES"
    CHACHA20 = "ChaCha20"
    THREE_DES = "3DES"
    DES = "DES"
    RC4 = "RC4"
    BLOWFISH = "Blowfish"
    MD5 = "MD5"
    SHA_1 = "SHA-1"
    SHA_2 = "SHA-2"
    SHA_3 = "SHA-3"
    HMAC = "HMAC"
    ML_KEM = "ML-KEM"
    ML_DSA = "ML-DSA"
    SLH_DSA = "SLH-DSA"


class CryptoFunction(StrEnum):
    KEYGEN = "keygen"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    SIGN = "sign"
    VERIFY = "verify"
    DIGEST = "digest"
    TAG = "tag"
    KEYDERIVE = "keyderive"
    UNKNOWN = "unknown"


class FindingSource(StrEnum):
    AST = "ast"
    AST_REFERENCE = "ast-reference"
    AST_PROTOCOL_STRING = "ast-protocol-string"
    SOURCE_CONSTANT = "source-constant"
    BINARY_SYMBOL = "binary-symbol"
    BINARY_CONSTANT = "binary-constant"
    BINARY_OID = "binary-oid"
    X509_PARSER = "x509-parser"
    PEM_PARSER = "pem-parser"
    SSH_KEY_PARSER = "ssh-key-parser"
    CONFIG_PARSER = "config-parser"
    MANIFEST = "manifest"


class TriageStatus(StrEnum):
    OPEN = "open"
    ACCEPTED_RISK = "accepted-risk"
    FALSE_POSITIVE = "false-positive"
    FIXED = "fixed"


class ScanStatus(StrEnum):
    QUEUED = "queued"
    INGESTING = "ingesting"
    SCANNING = "scanning"
    SCORING = "scoring"
    DONE = "done"
    FAILED = "failed"


class RiskBand(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Exposure(StrEnum):
    EXTERNAL = "external"
    INTERNAL = "internal"
    ISOLATED = "isolated"
    TEST = "test"


class Criticality(StrEnum):
    MISSION_CRITICAL = "mission-critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GraphNodeType(StrEnum):
    SYSTEM = "system"
    FILE = "file"
    ASSET = "asset"


class Location(BaseModel):
    path: str
    line: int | None = None
    offset: int | None = None
    layer: str | None = None


class RiskCost(BaseModel):
    pkBytesDelta: int
    wireBytesDelta: int
    opMsDelta: float


class Recommendation(BaseModel):
    action: str
    target: str | None = None
    cost: RiskCost


class Risk(BaseModel):
    score: float = Field(ge=0, le=100)
    band: RiskBand
    V: float
    F: float
    U: float
    E: float
    K: float
    X: float
    Y: float
    Z: float
    moscaMargin: float
    reason: str
    classicallyBroken: bool
    hndl: bool
    needsReview: bool


class Triage(BaseModel):
    status: TriageStatus = TriageStatus.OPEN
    note: str | None = None


class TriagePatch(BaseModel):
    status: TriageStatus
    note: str | None = None


class Finding(BaseModel):
    id: str
    kind: FindingKind
    surface: Surface
    family: Family | None
    displayName: str
    keySize: int | None = None
    mode: str | None = None
    curve: str | None = None
    function: CryptoFunction
    location: Location
    symbol: str
    snippet: str
    source: FindingSource
    confidence: float = Field(ge=0, le=1)
    risk: Risk | None = None
    recommendation: Recommendation | None = None
    triage: Triage


class ScanStats(BaseModel):
    files: int
    bytes: int
    seconds: float
    mbPerSec: float
    errors: int
    skippedPrefilter: int


class BandCounts(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class Scan(BaseModel):
    id: str
    target: str
    status: ScanStatus
    stats: ScanStats | None = None
    bands: BandCounts
    policyId: str
    crqcYears: int
    startedAt: datetime
    finishedAt: datetime | None = None


class ScanCreate(BaseModel):
    path: str | None = None
    policyId: str | None = None
    crqcYears: int | None = None


class RescoreRequest(BaseModel):
    crqcYears: int | None = None
    policyId: str | None = None


class RescoreResult(BaseModel):
    bands: BandCounts
    changed: list[Finding]


class Context(BaseModel):
    exposure: Exposure
    criticality: Criticality
    shelfLifeYears: int
    migrationYears: int


class ContextWithGlob(Context):
    glob: str


class Policy(BaseModel):
    id: str
    name: str
    crqcYears: int
    default: Context
    contexts: list[ContextWithGlob] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    type: GraphNodeType
    label: str
    band: RiskBand | None = None
    score: float | None = None
    occurrences: int
    parentId: str | None = None


class GraphEdge(BaseModel):
    source: str
    target: str


class Graph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class FindingPage(BaseModel):
    items: list[Finding]
    cursor: str | None = None
    total: int


class PqcCatalogEntry(BaseModel):
    family: Family
    displayName: str
    standard: str
    parameterSet: str
    securityCategory: int
    publicKeyBytes: int | None = None
    ciphertextOrSignatureBytes: int | None = None
    notes: str


class RemediationPlanItem(BaseModel):
    findingId: str
    band: RiskBand
    displayName: str
    location: Location
    action: str
    target: str | None = None


class RemediationPlan(BaseModel):
    scanId: str
    generatedAt: datetime
    items: list[RemediationPlanItem]


class HealthStatus(BaseModel):
    status: Literal["ok"]
    version: str
    time: datetime


class ErrorDetail(BaseModel):
    error: str
    message: str
