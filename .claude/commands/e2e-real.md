---
description: Run the real backend+frontend end-to-end integration scenario (the 10-step scan/triage/export/graph/hostile-upload flow) and report a PASS/FAIL table with evidence.
---

Invoke the `integration-runner` subagent (see `.claude/agents/integration-runner.md`) to
start the real backend and real frontend (MSW off) and run the full 10-step scenario. Do
not simulate any step or accept a mocked response as evidence. Report its PASS/FAIL table
verbatim plus the defect list.
