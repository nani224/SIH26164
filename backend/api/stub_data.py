"""In-memory Phase 0 stub data.

IMPORTANT: none of this comes from a real detection run. There is no
`ecdat` engine yet (that's Phase 1+). These are hand-built example payloads
that are internally consistent with the risk formula in backend/CLAUDE.md
(Score = 100 x V x F x U x E x K), so the frontend and contract tests have
something realistic to render/validate against. Do not treat the numbers
as measured precision/recall/risk output.
"""

from __future__ import annotations

from datetime import UTC, datetime

from api.models import (
    BandCounts,
    Context,
    ContextWithGlob,
    Criticality,
    CryptoFunction,
    Exposure,
    Family,
    Finding,
    FindingKind,
    FindingSource,
    Location,
    Policy,
    PqcCatalogEntry,
    Recommendation,
    Risk,
    RiskBand,
    RiskCost,
    Scan,
    ScanStats,
    ScanStatus,
    Surface,
    Triage,
    TriageStatus,
)
from engine.pqc import NIST_PQC_CATALOG

DEFAULT_POLICY = Policy(
    id="policy_default",
    name="Default NTRO baseline",
    crqcYears=10,
    default=Context(
        exposure=Exposure.INTERNAL,
        criticality=Criticality.MEDIUM,
        shelfLifeYears=5,
        migrationYears=3,
    ),
    contexts=[
        ContextWithGlob(
            glob="**/prod/**",
            exposure=Exposure.EXTERNAL,
            criticality=Criticality.MISSION_CRITICAL,
            shelfLifeYears=10,
            migrationYears=5,
        ),
        ContextWithGlob(
            glob="**/test/**",
            exposure=Exposure.TEST,
            criticality=Criticality.LOW,
            shelfLifeYears=1,
            migrationYears=1,
        ),
    ],
)

_FINDINGS: list[Finding] = [
    Finding(
        id="finding_001",
        kind=FindingKind.ALGORITHM,
        surface=Surface.SOURCE,
        family=Family.RSA,
        displayName="RSA-2048 key generation",
        keySize=2048,
        mode=None,
        curve=None,
        function=CryptoFunction.KEYGEN,
        location=Location(path="src/main/java/com/example/auth/KeyService.java", line=42, offset=None, layer=None),
        symbol="KeyPairGenerator.generateKeyPair",
        snippet="KeyPairGenerator gen = KeyPairGenerator.getInstance(\"RSA\"); gen.initialize(2048);",
        source=FindingSource.AST,
        confidence=0.92,
        risk=Risk(
            score=76.95, band=RiskBand.CRITICAL, V=1.0, F=0.9, U=1.0, E=0.95, K=0.9,
            X=12, Y=8, Z=10, moscaMargin=10,
            reason="Shor-vulnerable asymmetric keygen on an externally-exposed, mission-critical "
            "path; shelf life plus migration time exceeds the analyst's CRQC horizon.",
            classicallyBroken=False, hndl=True, needsReview=False,
        ),
        recommendation=Recommendation(
            action="Migrate to ML-KEM-768 for key establishment (hybrid with X25519 during transition)",
            target="ML-KEM-768",
            cost=RiskCost(pkBytesDelta=1184 - 256, wireBytesDelta=1088 - 256, opMsDelta=0.05),
        ),
        triage=Triage(status=TriageStatus.OPEN),
    ),
    Finding(
        id="finding_002",
        kind=FindingKind.KEY,
        surface=Surface.CERTIFICATE,
        family=Family.RSA,
        displayName="Unencrypted RSA private key",
        keySize=2048,
        mode=None,
        curve=None,
        function=CryptoFunction.SIGN,
        location=Location(path="deploy/secrets/server.key", line=None, offset=0, layer=None),
        symbol="PRIVATE KEY",
        snippet="-----BEGIN RSA PRIVATE KEY-----",
        source=FindingSource.PEM_PARSER,
        confidence=0.98,
        risk=Risk(
            score=92.0, band=RiskBand.CRITICAL, V=1.0, F=1.0, U=1.0, E=1.0, K=0.92,
            X=10, Y=8, Z=10, moscaMargin=8,
            reason="Unencrypted private key found outside a test path — "
            "forced to score >= 90 per policy regardless of other factors.",
            classicallyBroken=False, hndl=True, needsReview=False,
        ),
        recommendation=Recommendation(
            action="Move key material to a hardware-backed store (HSM/KMS) and rotate; "
            "plan migration to ML-DSA-65 for the associated signing use",
            target="ML-DSA-65",
            cost=RiskCost(pkBytesDelta=1952 - 256, wireBytesDelta=3309 - 256, opMsDelta=0.08),
        ),
        triage=Triage(status=TriageStatus.OPEN),
    ),
    Finding(
        id="finding_003",
        kind=FindingKind.ALGORITHM,
        surface=Surface.CONFIG,
        family=Family.THREE_DES,
        displayName="3DES-CBC cipher suite enabled",
        keySize=168,
        mode="CBC",
        curve=None,
        function=CryptoFunction.ENCRYPT,
        location=Location(path="deploy/nginx/nginx.conf", line=17, offset=None, layer=None),
        symbol="ssl_ciphers",
        snippet="ssl_ciphers 'DES-CBC3-SHA:...';",
        source=FindingSource.CONFIG_PARSER,
        confidence=0.9,
        risk=Risk(
            score=35.84, band=RiskBand.HIGH, V=1.0, F=0.8, U=0.8, E=0.7, K=0.8,
            X=7, Y=6, Z=10, moscaMargin=3,
            reason="Deprecated 64-bit block cipher accepted by an internet-facing TLS endpoint; "
            "Sweet32-class weaknesses plus reduced Grover-adjusted margin.",
            classicallyBroken=False, hndl=False, needsReview=False,
        ),
        recommendation=Recommendation(
            action="Remove 3DES from the cipher list; standardize on AES-256-GCM / ChaCha20-Poly1305",
            target="AES-256-GCM",
            cost=RiskCost(pkBytesDelta=0, wireBytesDelta=0, opMsDelta=-0.01),
        ),
        triage=Triage(status=TriageStatus.OPEN),
    ),
    Finding(
        id="finding_004",
        kind=FindingKind.ALGORITHM,
        surface=Surface.SOURCE,
        family=Family.MD5,
        displayName="MD5 digest used for artifact checksum",
        keySize=None,
        mode=None,
        curve=None,
        function=CryptoFunction.DIGEST,
        location=Location(path="tools/verify.cpp", line=88, offset=None, layer=None),
        symbol="MD5_Final",
        snippet="MD5_Init(&ctx); MD5_Update(&ctx, buf, len); MD5_Final(digest, &ctx);",
        source=FindingSource.BINARY_SYMBOL,
        confidence=0.85,
        risk=Risk(
            score=21.0, band=RiskBand.MEDIUM, V=1.0, F=0.7, U=1.0, E=0.6, K=0.5,
            X=3, Y=2, Z=10, moscaMargin=-5,
            reason="MD5 is classically broken (collision attacks); U forced to 1 regardless of "
            "horizon. Non-security checksum use lowers exposure/criticality factors.",
            classicallyBroken=True, hndl=False, needsReview=False,
        ),
        recommendation=Recommendation(
            action="Replace with SHA-256 (non-cryptographic checksum use may use a fast "
            "non-crypto hash instead, e.g. xxHash)",
            target="SHA-2-256",
            cost=RiskCost(pkBytesDelta=0, wireBytesDelta=0, opMsDelta=0.0),
        ),
        triage=Triage(status=TriageStatus.OPEN),
    ),
    Finding(
        id="finding_005",
        kind=FindingKind.PROTOCOL,
        surface=Surface.SOURCE,
        family=Family.HMAC,
        displayName="HMAC-SHA1 message authentication",
        keySize=None,
        mode=None,
        curve=None,
        function=CryptoFunction.TAG,
        location=Location(path="internal/auth/token.go", line=54, offset=None, layer=None),
        symbol="hmac.New(sha1.New, key)",
        snippet="mac := hmac.New(sha1.New, key)",
        source=FindingSource.AST_REFERENCE,
        confidence=0.68,
        risk=Risk(
            score=15.12, band=RiskBand.MEDIUM, V=1.0, F=0.6, U=0.7, E=0.6, K=0.6,
            X=5, Y=3, Z=10, moscaMargin=-2,
            reason="SHA-1-based HMAC on an internal token path; HMAC-SHA1 is not broken as a "
            "MAC but SHA-1 is deprecated and confidence is below the review threshold.",
            classicallyBroken=False, hndl=False, needsReview=True,
        ),
        recommendation=Recommendation(
            action="Move to HMAC-SHA-256",
            target="HMAC-SHA-2-256",
            cost=RiskCost(pkBytesDelta=0, wireBytesDelta=0, opMsDelta=0.0),
        ),
        triage=Triage(status=TriageStatus.OPEN),
    ),
    Finding(
        id="finding_006",
        kind=FindingKind.ALGORITHM,
        surface=Surface.SOURCE,
        family=Family.AES,
        displayName="AES-256-GCM authenticated encryption",
        keySize=256,
        mode="GCM",
        curve=None,
        function=CryptoFunction.ENCRYPT,
        location=Location(path="app/crypto/vault.py", line=23, offset=None, layer=None),
        symbol="AESGCM",
        snippet="aesgcm = AESGCM(key); ct = aesgcm.encrypt(nonce, data, aad)",
        source=FindingSource.AST,
        confidence=0.95,
        risk=Risk(
            score=0.63, band=RiskBand.LOW, V=0.1, F=0.5, U=0.5, E=0.5, K=0.5,
            X=2, Y=2, Z=10, moscaMargin=-6,
            reason="AES-256 retains ~128-bit security under Grover's algorithm; negligible "
            "residual quantum risk at current parameters.",
            classicallyBroken=False, hndl=False, needsReview=False,
        ),
        recommendation=None,
        triage=Triage(status=TriageStatus.OPEN),
    ),
]

_SCAN = Scan(
    id="scan_stub_001",
    target="example-monorepo",
    status=ScanStatus.DONE,
    stats=ScanStats(files=482, bytes=18_340_221, seconds=3.9, mbPerSec=4.48, errors=0, skippedPrefilter=311),
    bands=BandCounts(critical=2, high=1, medium=2, low=1),
    policyId=DEFAULT_POLICY.id,
    crqcYears=10,
    startedAt=datetime(2026, 9, 17, 12, 0, 0, tzinfo=UTC),
    finishedAt=datetime(2026, 9, 17, 12, 0, 4, tzinfo=UTC),
)

PQC_CATALOG: list[PqcCatalogEntry] = [spec.to_catalog_entry() for spec in NIST_PQC_CATALOG]


def list_findings() -> list[Finding]:
    """Seed data only as of Phase 2 -- api/db.py's init_db() loads this once
    into the database; runtime reads/writes go through api/store.py instead.
    """
    return list(_FINDINGS)


def default_scan() -> Scan:
    return _SCAN.model_copy(deep=True)
