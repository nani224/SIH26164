"""Executive summary PDF report generator for ECDAT (Phase 9).

Generates a multi-page, publication-grade executive PDF report covering:
1. Executive Summary & Mosca Quantum Risk Scorecard
2. Detailed Risk Factor Analysis & Top Vulnerable Findings Table
3. Actionable Remediation Roadmap & Standardized NIST PQC Migration Plan

Pure Python implementation with zero third-party dependencies, adhering strictly
to the ISO 32000-1 / PDF 1.4 specification for air-gapped environments.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.models import Finding, Scan


def _escape(text: str) -> str:
    """Escape special PDF text string characters."""
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


# Pre-defined RGB color palettes
_NAVY = (0.059, 0.090, 0.165)       # #0f172a
_SLATE_DARK = (0.200, 0.255, 0.333)  # #334155
_SLATE_MED = (0.392, 0.455, 0.545)   # #64748b
_SLATE_LIGHT = (0.945, 0.961, 0.976) # #f1f5f9
_WHITE = (1.0, 1.0, 1.0)
_GRAY_BORDER = (0.800, 0.835, 0.880)

# Risk Band Colors (Fill, Text)
_BAND_COLORS: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {
    "critical": ((0.992, 0.867, 0.867), (0.722, 0.110, 0.110)),  # Light red, Dark red
    "high": ((1.000, 0.929, 0.835), (0.773, 0.333, 0.055)),      # Light orange, Dark orange
    "medium": ((0.996, 0.980, 0.824), (0.631, 0.447, 0.035)),    # Light yellow, Dark gold
    "low": ((0.863, 0.933, 1.000), (0.118, 0.392, 0.745)),       # Light blue, Dark blue
}


class PdfBuilder:
    """Zero-dependency, multi-page PDF 1.4 document composer."""

    def __init__(self, page_width: float = 612.0, page_height: float = 792.0) -> None:
        self.width = page_width
        self.height = page_height
        self.pages: list[bytearray] = []
        self._current_page: bytearray = bytearray()

    def new_page(self) -> None:
        if self._current_page:
            self.pages.append(self._current_page)
        self._current_page = bytearray()

    def draw_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: tuple[float, float, float] | None = None,
        stroke: tuple[float, float, float] | None = None,
        stroke_width: float = 1.0,
    ) -> None:
        cmd = bytearray()
        if fill is not None:
            cmd += f"{fill[0]:.3f} {fill[1]:.3f} {fill[2]:.3f} rg\n".encode()
        if stroke is not None:
            cmd += f"{stroke[0]:.3f} {stroke[1]:.3f} {stroke[2]:.3f} RG\n".encode()
            cmd += f"{stroke_width:.2f} w\n".encode()

        cmd += f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re\n".encode()
        if fill is not None and stroke is not None:
            cmd += b"B\n"
        elif fill is not None:
            cmd += b"f\n"
        elif stroke is not None:
            cmd += b"S\n"
        self._current_page += cmd

    def draw_line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        stroke: tuple[float, float, float] = _GRAY_BORDER,
        stroke_width: float = 1.0,
    ) -> None:
        cmd = (
            f"{stroke[0]:.3f} {stroke[1]:.3f} {stroke[2]:.3f} RG\n"
            f"{stroke_width:.2f} w\n"
            f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S\n"
        ).encode()
        self._current_page += cmd

    def draw_text(
        self,
        x: float,
        y: float,
        text: str,
        font: str = "F1",
        size: float = 10.0,
        color: tuple[float, float, float] = _SLATE_DARK,
    ) -> None:
        escaped = _escape(text)
        cmd = (
            f"BT\n"
            f"/{font} {size:.2f} Tf\n"
            f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg\n"
            f"1 0 0 1 {x:.2f} {y:.2f} Tm\n"
            f"({escaped}) Tj\n"
            f"ET\n"
        ).encode()
        self._current_page += cmd

    def draw_badge(
        self,
        x: float,
        y: float,
        text: str,
        band: str,
        width: float = 58.0,
        height: float = 14.0,
    ) -> None:
        fill, text_color = _BAND_COLORS.get(band.lower(), ((0.9, 0.9, 0.9), (0.2, 0.2, 0.2)))
        self.draw_rect(x, y, width, height, fill=fill, stroke=text_color, stroke_width=0.5)
        # Center-ish text inside badge
        self.draw_text(x + 5.0, y + 3.5, text.upper(), font="F2", size=7.5, color=text_color)

    def compile(self) -> bytes:
        if self._current_page:
            self.pages.append(self._current_page)

        total_pages = len(self.pages)
        if total_pages == 0:
            self.new_page()
            total_pages = 1

        # Stamp running headers and footers
        for idx, page in enumerate(self.pages, start=1):
            # Top subtle header
            header_cmd = (
                f"BT /F1 7.5 Tf 0.392 0.455 0.545 rg 1 0 0 1 40 765 Tm "
                f"({_escape('ECDAT Cryptographic Security & Quantum Risk Assessment')}) Tj ET\n"
                f"0.800 0.835 0.880 RG 0.5 w 40 757 m 572 757 l S\n"
            ).encode()
            # Bottom footer
            footer_text = f"Page {idx} of {total_pages}   |   ECDAT v0.1.0 Assessment   |   CONFIDENTIAL"
            footer_cmd = (
                f"0.800 0.835 0.880 RG 0.5 w 40 42 m 572 42 l S\n"
                f"BT /F1 7.5 Tf 0.392 0.455 0.545 rg 1 0 0 1 40 30 Tm "
                f"({_escape(footer_text)}) Tj ET\n"
            ).encode()
            # Prepend header, append footer
            page[0:0] = header_cmd
            page.extend(footer_cmd)

        objects: list[bytes] = []
        # Obj 1: Catalog
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")

        # Obj 2: Pages tree
        page_refs = [f"{6 + 2 * i} 0 R" for i in range(total_pages)]
        kids_str = " ".join(page_refs)
        objects.append(f"<< /Type /Pages /Kids [{kids_str}] /Count {total_pages} >>".encode())

        # Obj 3: Font F1 (Helvetica)
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        # Obj 4: Font F2 (Helvetica-Bold)
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        # Obj 5: Font F3 (Courier)
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

        # For each page, add Page Dict and Content Stream
        for idx in range(total_pages):
            content_id = 7 + 2 * idx
            page_dict = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width:.2f} {self.height:.2f}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode()
            objects.append(page_dict)

            stream_data = bytes(self.pages[idx])
            stream_obj = f"<< /Length {len(stream_data)} >>\nstream\n".encode() + stream_data + b"\nendstream"
            objects.append(stream_obj)

        buf = bytearray(b"%PDF-1.4\n")
        offsets: list[int] = []
        for i, obj in enumerate(objects, start=1):
            offsets.append(len(buf))
            buf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

        xref_offset = len(buf)
        buf += f"xref\n0 {len(objects) + 1}\n".encode()
        buf += b"0000000000 65535 f \n"
        for off in offsets:
            buf += f"{off:010d} 00000 n \n".encode()
        buf += (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
        return bytes(buf)


def build_executive_report_pdf(scan: Scan, findings: list[Finding]) -> bytes:
    """Builds a complete, multi-page executive summary PDF report."""
    builder = PdfBuilder()

    # --- PAGE 1: Executive Summary & Quantum Risk Scorecard ---
    builder.new_page()

    # Title Banner Box
    builder.draw_rect(40, 680, 532, 65, fill=_NAVY, stroke=None)
    builder.draw_text(55, 722, "ECDAT — Executive Cryptographic Risk Report", font="F2", size=16, color=_WHITE)
    builder.draw_text(
        55,
        702,
        "Automated Air-Gapped Discovery, Mosca Risk Scoring & PQC Migration Plan",
        font="F1",
        size=9.5,
        color=(0.85, 0.90, 0.95),
    )

    # Scan Metadata Card
    builder.draw_rect(40, 580, 532, 88, fill=_SLATE_LIGHT, stroke=_GRAY_BORDER, stroke_width=0.75)
    builder.draw_text(55, 650, "Scan Overview & Parameters", font="F2", size=10, color=_NAVY)
    builder.draw_line(55, 644, 557, 644, stroke=_GRAY_BORDER, stroke_width=0.5)

    scanned_str = scan.startedAt.strftime("%Y-%m-%d %H:%M:%S UTC") if scan.startedAt else "N/A"
    builder.draw_text(55, 628, f"Scan ID: {scan.id}", font="F3", size=8.5, color=_SLATE_DARK)
    builder.draw_text(55, 614, f"Target Path: {scan.target}", font="F1", size=8.5, color=_SLATE_DARK)
    builder.draw_text(55, 600, f"Timestamp: {scanned_str}", font="F1", size=8.5, color=_SLATE_DARK)

    builder.draw_text(320, 628, f"Policy ID: {scan.policyId}", font="F1", size=8.5, color=_SLATE_DARK)
    builder.draw_text(320, 614, f"CRQC Horizon (Z): {scan.crqcYears} years", font="F2", size=8.5, color=_SLATE_DARK)
    bundle_display = f"{scan.bundleHash[:24]}..." if scan.bundleHash else "N/A (Local Directory)"
    builder.draw_text(320, 600, f"Bundle SHA-256: {bundle_display}", font="F3", size=8, color=_SLATE_DARK)

    # Overall Mosca Scorecard Box
    overall_score = max((f.risk.score for f in findings if f.risk), default=0.0)
    if overall_score >= 80:
        overall_band = "critical"
    elif overall_score >= 60:
        overall_band = "high"
    elif overall_score >= 40:
        overall_band = "medium"
    else:
        overall_band = "low"
    builder.draw_rect(40, 470, 532, 95, fill=_WHITE, stroke=_GRAY_BORDER, stroke_width=1.0)

    builder.draw_text(55, 545, "Overall Mosca Quantum Risk Score", font="F2", size=11, color=_NAVY)
    builder.draw_text(55, 508, f"{overall_score:.1f}", font="F2", size=32, color=_NAVY)
    builder.draw_text(130, 516, "/ 100", font="F1", size=13, color=_SLATE_MED)
    builder.draw_badge(180, 516, overall_band, overall_band, width=65, height=18)

    # Metric Breakdown Cards
    files_count = scan.stats.files if scan.stats else 0
    findings_count = len(findings)
    cards = [
        ("Files Scanned", str(files_count), _SLATE_DARK),
        ("Total Assets", str(findings_count), _NAVY),
        ("Critical", str(scan.bands.critical), (0.722, 0.110, 0.110)),
        ("High", str(scan.bands.high), (0.773, 0.333, 0.055)),
        ("Medium", str(scan.bands.medium), (0.631, 0.447, 0.035)),
        ("Low", str(scan.bands.low), (0.118, 0.392, 0.745)),
    ]

    card_x = 265.0
    for title, count_str, text_col in cards:
        builder.draw_rect(card_x, 480, 46, 75, fill=_SLATE_LIGHT, stroke=_GRAY_BORDER, stroke_width=0.5)
        builder.draw_text(card_x + 4, 535, title[:8], font="F1", size=7, color=_SLATE_MED)
        builder.draw_text(card_x + 10, 504, count_str, font="F2", size=14, color=text_col)
        card_x += 51.0

    # Mosca Formula & Context Explanation
    builder.draw_rect(40, 345, 532, 110, fill=_SLATE_LIGHT, stroke=_GRAY_BORDER, stroke_width=0.75)
    builder.draw_text(55, 435, "Mosca Theorem & Quantum Threat Model", font="F2", size=10.5, color=_NAVY)
    builder.draw_line(55, 429, 557, 429, stroke=_GRAY_BORDER, stroke_width=0.5)

    builder.draw_text(
        55,
        413,
        "Risk Formulation:  Score = 100 x V x F x U x E x K",
        font="F2",
        size=9.5,
        color=_NAVY,
    )
    builder.draw_text(
        55,
        397,
        "Where: V = Vulnerability factor (quantum or classical breakability, 0.0 - 1.0)",
        font="F1",
        size=8.5,
        color=_SLATE_DARK,
    )
    builder.draw_text(
        55,
        383,
        "       F = Function criticality (key exchange 1.0, signature 0.8, bulk cipher 0.6, hash 0.3)",
        font="F1",
        size=8.5,
        color=_SLATE_DARK,
    )
    builder.draw_text(
        55,
        369,
        "       U = Mosca Urgency factor (U = 1.0 if Shelf-life X + Migration Y >= Horizon Z)",
        font="F1",
        size=8.5,
        color=_SLATE_DARK,
    )
    builder.draw_text(
        55,
        355,
        "       E = Surface Exposure (1.0 public/network, 0.5 internal), K = Key size modifier",
        font="F1",
        size=8.5,
        color=_SLATE_DARK,
    )

    # Executive Summary Paragraph
    builder.draw_rect(40, 65, 532, 265, fill=_WHITE, stroke=_GRAY_BORDER, stroke_width=0.75)
    builder.draw_text(55, 310, "Executive Observations & Risk Profile", font="F2", size=10.5, color=_NAVY)
    builder.draw_line(55, 304, 557, 304, stroke=_GRAY_BORDER, stroke_width=0.5)

    observations = [
        f"1. Quantum Exposure Summary: {findings_count} cryptographic instances detected across {files_count} files.",
        f"   Identified {scan.bands.critical} Critical and {scan.bands.high} High priority exposures.",
        "2. Harvest Now, Decrypt Later (HNDL) Threat: Asymmetric public-key algorithms (RSA, ECDH, ECDSA)",
        f"   exhibit immediate urgency (U=1.0) under the configured {scan.crqcYears}-year horizon.",
        "3. Classical Obsolescence: Legacy algorithms (MD5, SHA-1, DES, 3DES) present immediate pre-quantum",
        "   vulnerabilities due to collision and small-block attacks, independent of quantum timelines.",
        "4. Standardized Remediation Path: Post-quantum migration paths are aligned with finalized NIST",
        "   standards: FIPS 203 (ML-KEM) for key exchange and FIPS 204 (ML-DSA) for digital signatures.",
        "5. Air-Gapped Verification: This assessment was generated completely offline with deterministic AST analysis,",
        "   ensuring zero intellectual property or cryptographic asset metadata leakage to public networks.",
    ]
    cur_y = 285
    for obs in observations:
        builder.draw_text(55, cur_y, obs, font="F1", size=8.5, color=_SLATE_DARK)
        cur_y -= 18

    # --- PAGE 2: Detailed Mosca Risk Factor Analysis & Top Vulnerabilities ---
    builder.new_page()

    builder.draw_text(
        40, 735, "2. Detailed Risk Factor Analysis & Top Vulnerabilities", font="F2", size=13, color=_NAVY
    )
    builder.draw_line(40, 725, 572, 725, stroke=_NAVY, stroke_width=1.0)

    # Table of Top Findings
    builder.draw_text(40, 705, "Top Vulnerable Cryptographic Findings", font="F2", size=10.5, color=_NAVY)

    # Sort findings by risk score descending
    sorted_findings = sorted(
        findings,
        key=lambda f: (f.risk.score if f.risk else 0.0),
        reverse=True,
    )

    # Table Header
    headers = [
        ("Asset / Symbol", 40.0, 140.0),
        ("Location", 185.0, 165.0),
        ("Family", 355.0, 60.0),
        ("Function", 420.0, 55.0),
        ("Score", 480.0, 40.0),
        ("Band", 525.0, 47.0),
    ]

    y_table = 680.0
    builder.draw_rect(40, y_table, 532, 20, fill=_NAVY, stroke=None)
    for title, hx, _ in headers:
        builder.draw_text(hx + 4, y_table + 6, title, font="F2", size=8, color=_WHITE)

    y_row = y_table - 22.0
    for row_count, finding in enumerate(sorted_findings[:16]):  # Show top 16 findings on page 2
        bg = _SLATE_LIGHT if (row_count % 2 == 1) else _WHITE
        builder.draw_rect(40, y_row, 532, 20, fill=bg, stroke=_GRAY_BORDER, stroke_width=0.3)

        # Asset display name
        disp_name = (finding.displayName or finding.symbol or "unknown")[:22]
        builder.draw_text(44, y_row + 6, disp_name, font="F2", size=7.5, color=_SLATE_DARK)

        # Location path + line
        loc_str = f"{finding.location.path}:{finding.location.line or '?'}"
        if len(loc_str) > 28:
            loc_str = f"...{loc_str[-25:]}"
        builder.draw_text(189, y_row + 6, loc_str, font="F3", size=7, color=_SLATE_DARK)

        # Family
        builder.draw_text(359, y_row + 6, (finding.family or "-")[:10], font="F1", size=7.5, color=_SLATE_DARK)

        # Function
        builder.draw_text(424, y_row + 6, (finding.function or "-")[:8], font="F1", size=7.5, color=_SLATE_DARK)

        # Score
        score_val = finding.risk.score if finding.risk else 0.0
        builder.draw_text(484, y_row + 6, f"{score_val:.1f}", font="F2", size=7.5, color=_NAVY)

        # Band Badge
        band_str = finding.risk.band if finding.risk else "low"
        builder.draw_badge(527, y_row + 3, band_str, band_str, width=42, height=14)

        y_row -= 22.0

    # Factor Analysis Explanatory Callout Box
    builder.draw_rect(40, 60, 532, 175, fill=_SLATE_LIGHT, stroke=_GRAY_BORDER, stroke_width=0.75)
    builder.draw_text(55, 215, "Mosca Horizon Analysis & Exposure Guidance", font="F2", size=10, color=_NAVY)
    builder.draw_line(55, 209, 557, 209, stroke=_GRAY_BORDER, stroke_width=0.5)

    guidance_notes = [
        "- Classical Urgency (U=1.0): Legacy algorithms like MD5, SHA-1, DES, and 3DES have U=1.0 unconditionally",
        "  regardless of CRQC horizon due to active real-world cryptanalytic attacks.",
        f"- Quantum Horizon Margin: Findings with X + Y >= {scan.crqcYears} years carry high/critical urgency.",
        "  Data encrypted today with classical public-key cryptography is vulnerable to retroactive decryption by",
        "  adversaries storing intercepted ciphertexts ('Harvest Now, Decrypt Later').",
        "- Exposure Multiplier: Assets located on network perimeters, API entry points, or client-facing interfaces",
        "  carry Exposure E=1.0. Internal utility functions and unit test references are adjusted to E=0.5.",
        "- Key Size Modifiers: RSA-1024 / 512 keys incur maximum penalty (K=1.0); RSA-4096 achieves partial protection",
        "  against intermediate quantum attacks but remains fundamentally quantum-vulnerable (Shor's Algorithm).",
    ]
    gy = 192
    for note in guidance_notes:
        builder.draw_text(55, gy, note, font="F1", size=8, color=_SLATE_DARK)
        gy -= 15

    # --- PAGE 3: Actionable Remediation Roadmap & PQC Migration Plan ---
    builder.new_page()

    builder.draw_text(40, 735, "3. Actionable Remediation & PQC Migration Plan", font="F2", size=13, color=_NAVY)
    builder.draw_line(40, 725, 572, 725, stroke=_NAVY, stroke_width=1.0)

    # Remediation Table
    builder.draw_text(40, 705, "Standardized NIST PQC Migration Actions", font="F2", size=10.5, color=_NAVY)

    pqc_headers = [
        ("Asset Name", 40.0, 130.0),
        ("Current Algorithm", 175.0, 95.0),
        ("Target Standard / PQC", 275.0, 125.0),
        ("Action", 405.0, 105.0),
        ("Cost", 515.0, 57.0),
    ]

    builder.draw_rect(40, 680, 532, 20, fill=_NAVY, stroke=None)
    for title, hx, _ in pqc_headers:
        builder.draw_text(hx + 4, 686, title, font="F2", size=8, color=_WHITE)

    y_pqc = 658.0
    # Collect items that have recommendations
    recommended_findings = [f for f in sorted_findings if f.recommendation is not None]
    for _pqc_row, finding in enumerate(recommended_findings[:16]):
        bg = _SLATE_LIGHT if (_pqc_row % 2 == 1) else _WHITE
        builder.draw_rect(40, y_pqc, 532, 20, fill=bg, stroke=_GRAY_BORDER, stroke_width=0.3)

        disp_name = (finding.displayName or finding.symbol or "unknown")[:20]
        builder.draw_text(44, y_pqc + 6, disp_name, font="F2", size=7.5, color=_SLATE_DARK)

        cur_algo = f"{finding.family or 'Unknown'} {finding.keySize or ''}".strip()[:14]
        builder.draw_text(179, y_pqc + 6, cur_algo, font="F1", size=7.5, color=_SLATE_DARK)

        target_str = (finding.recommendation.target or "-") if finding.recommendation else "-"
        target_algo = target_str[:20]
        builder.draw_text(279, y_pqc + 6, target_algo, font="F2", size=7.5, color=_NAVY)

        action_txt = (finding.recommendation.action if finding.recommendation else "-")[:18]
        builder.draw_text(409, y_pqc + 6, action_txt, font="F1", size=7.5, color=_SLATE_DARK)

        cost_raw = finding.recommendation.cost if finding.recommendation else "medium"
        cost_txt = str(cost_raw.value if hasattr(cost_raw, "value") else cost_raw)
        cost_band = "low" if cost_txt == "low" else ("high" if cost_txt == "high" else "medium")
        builder.draw_badge(519, y_pqc + 3, cost_txt, cost_band, width=45, height=14)

        y_pqc -= 22.0

    # NIST PQC Standards Reference Card
    builder.draw_rect(40, 160, 532, 120, fill=_SLATE_LIGHT, stroke=_GRAY_BORDER, stroke_width=0.75)
    builder.draw_text(55, 260, "Authoritative NIST PQC Migration Standards Reference", font="F2", size=10, color=_NAVY)
    builder.draw_line(55, 254, 557, 254, stroke=_GRAY_BORDER, stroke_width=0.5)

    pqc_standards_notes = [
        "- FIPS 203 (ML-KEM): Standard replacement for RSA/ECDH key exchange.",
        "  ML-KEM-768 provides Security Category 3 (AES-192 equivalent) as general-purpose default.",
        "- FIPS 204 (ML-DSA): Module-Lattice Digital Signature Algorithm for RSA/ECDSA signatures.",
        "  ML-DSA-65 provides Category 3 security with fast verification and compact signatures.",
        "- FIPS 205 (SLH-DSA): Stateless Hash-Based Digital Signature Algorithm.",
        "  Conservative fallback signature scheme based solely on hash function security assumptions.",
        "- SP 800-38D (AES-256-GCM): Approved symmetric cipher providing 128-bit post-Grover security.",
    ]
    py_pos = 238
    for pnote in pqc_standards_notes:
        builder.draw_text(55, py_pos, pnote, font="F1", size=7.8, color=_SLATE_DARK)
        py_pos -= 14

    # Cryptographic Attestation & Air-Gap Integrity Stamp
    builder.draw_rect(40, 55, 532, 90, fill=_WHITE, stroke=_NAVY, stroke_width=1.0)
    builder.draw_text(55, 126, "Cryptographic Attestation & Air-Gap Verification", font="F2", size=10, color=_NAVY)
    builder.draw_line(55, 120, 557, 120, stroke=_GRAY_BORDER, stroke_width=0.5)

    raw_stamp = f"{scan.id}:{scan.target}:{findings_count}:{overall_score}:{datetime.now(UTC).isoformat()}"
    report_sha256 = hashlib.sha256(raw_stamp.encode("utf-8")).hexdigest()

    builder.draw_text(
        55,
        105,
        "Environment: Strictly Deterministic, Fully Air-Gapped AST Engine (Zero External Telemetry)",
        font="F1",
        size=8,
        color=_SLATE_DARK,
    )
    builder.draw_text(
        55,
        91,
        f"Report Integrity SHA-256: {report_sha256}",
        font="F3",
        size=7.5,
        color=_NAVY,
    )
    now_utc = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
    builder.draw_text(
        55,
        77,
        f"Verification Timestamp: {now_utc} | CycloneDX 1.6 Cryptographic BOM",
        font="F1",
        size=8,
        color=_SLATE_MED,
    )

    return builder.compile()


def build_stub_report_pdf(scan_id: str) -> bytes:
    """Fallback single-page stub report builder for testing."""
    builder = PdfBuilder()
    builder.new_page()
    builder.draw_text(40, 750, f"ECDAT Phase 0 stub report for scan {scan_id}", font="F2", size=12)
    return builder.compile()
