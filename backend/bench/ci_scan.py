"""CI-facing scan + gate + report: the script `.github/actions/ecdat-scan/`
(the reusable Action) and this repo's own workflows both run. Loads a
`.ecdat-policy.yml` (risk-scoring policy + gate rules, see the root
`.ecdat-policy.yml` for the schema), runs `engine.scanner.scan()` against
a target path, writes a JSON findings file and a Markdown findings table
(for `post_pr_comment.py` to post), and exits non-zero if any finding is
at or above the policy's `gate.failOnBand`.

Deliberately does not use the running API/DB at all -- CI has no server
to talk to, and shouldn't need one just to scan a checked-out repo.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.models import Context, ContextWithGlob, Finding, Policy, RiskBand  # noqa: E402
from engine.scanner import scan  # noqa: E402

_BAND_SEVERITY: dict[str, int] = {
    RiskBand.LOW.value: 1,
    RiskBand.MEDIUM.value: 2,
    RiskBand.HIGH.value: 3,
    RiskBand.CRITICAL.value: 4,
}


def _load_policy_and_gate(policy_path: Path) -> tuple[Policy, dict[str, Any]]:
    raw = yaml.safe_load(policy_path.read_text())
    policy = Policy(
        id="ci-scan",
        name="CI scan policy",
        crqcYears=raw["crqcYears"],
        default=Context(**raw["default"]),
        contexts=[ContextWithGlob(**c) for c in raw.get("contexts", [])],
    )
    gate = raw.get("gate", {"failOnBand": "critical", "precisionFloor": 0.95})
    return policy, gate


def _findings_table(findings: list[Finding]) -> str:
    if not findings:
        return "No cryptographic findings.\n"
    header = "| Band | Score | Family | Function | Location | Recommendation |\n"
    header += "|---|---|---|---|---|---|\n"
    rows = []
    for f in sorted(findings, key=lambda x: -(x.risk.score if x.risk else 0)):
        band = f.risk.band.value if f.risk else "n/a"
        score = f"{f.risk.score:.1f}" if f.risk else "n/a"
        family = f.family.value if f.family else "n/a"
        location = f"`{f.location.path}`" + (f":{f.location.line}" if f.location.line else "")
        target = (f.recommendation.target or "n/a") if f.recommendation else "n/a"
        rows.append(f"| {band} | {score} | {family} | {f.function.value} | {location} | {target} |")
    return header + "\n".join(rows) + "\n"


def _worst_band(findings: list[Finding]) -> str | None:
    worst: str | None = None
    worst_severity = -1
    for f in findings:
        if f.risk is None:
            continue
        severity = _BAND_SEVERITY[f.risk.band.value]
        if severity > worst_severity:
            worst_severity = severity
            worst = f.risk.band.value
    return worst


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, help="Directory or file to scan")
    parser.add_argument("--policy", default=".ecdat-policy.yml", help="Path to .ecdat-policy.yml")
    parser.add_argument("--json-output", default=None, help="Write findings + gate result as JSON here")
    parser.add_argument("--markdown-output", default=None, help="Write a Markdown findings table here")
    args = parser.parse_args()

    target = Path(args.path)
    policy, gate = _load_policy_and_gate(Path(args.policy))
    result = scan(target, policy)

    fail_on_band = gate.get("failOnBand", "critical")
    fail_on_severity = _BAND_SEVERITY.get(fail_on_band, _BAND_SEVERITY["critical"])
    blocking = [
        f for f in result.findings
        if f.risk is not None and _BAND_SEVERITY[f.risk.band.value] >= fail_on_severity
    ]
    passed = not blocking

    markdown = (
        f"## ECDAT scan: {len(result.findings)} finding(s), "
        f"worst band **{_worst_band(result.findings) or 'none'}**\n\n"
        f"{_findings_table(result.findings)}\n"
        + (
            f"**BLOCKED**: {len(blocking)} finding(s) at or above the gate band (`{fail_on_band}`).\n"
            if blocking
            else f"No findings at or above the gate band (`{fail_on_band}`).\n"
        )
    )
    print(markdown)

    if args.markdown_output:
        Path(args.markdown_output).write_text(markdown)
    if args.json_output:
        payload = {
            "passed": passed,
            "failOnBand": fail_on_band,
            "findingCount": len(result.findings),
            "blockingCount": len(blocking),
            "findings": [json.loads(f.model_dump_json()) for f in result.findings],
        }
        Path(args.json_output).write_text(json.dumps(payload, indent=2))

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
