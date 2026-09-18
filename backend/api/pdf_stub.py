"""Minimal, dependency-free placeholder PDF for GET /scans/{id}/report.pdf.

This is NOT the real executive report (that's Phase 9, self-hosted fonts,
proper layout). It's a hand-built single-page PDF so the endpoint returns a
genuinely valid `application/pdf` byte stream today.
"""

from __future__ import annotations

from api.pdf_report import build_stub_report_pdf

__all__ = ["build_stub_report_pdf"]
