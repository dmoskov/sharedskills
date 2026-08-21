---
name: environmental-scan
description: Scan the external environment for threats and opportunities affecting this project — CVEs in your dependencies, API/SDK changes, notable releases and research
triggers:
  - "environmental scan"
  - "check for security vulnerabilities"
  - "scan for updates"
  - "check dependencies for CVEs"
  - "what changed upstream"
tools_required:
  - Bash
  - Read
  - Glob
  - Grep
  - WebSearch
  - WebFetch
---

# Environmental Scanning Skill

Look outward: find security advisories, breaking upstream changes, and relevant new
releases/research that affect the current project, and produce a severity-ranked
intelligence report. Runs entirely from the session using web search/fetch — no
database, feeds infrastructure, or scheduled jobs required.

## When to Use

- Periodically (weekly is a good cadence) on any actively developed project
- Before upgrading dependencies or planning a maintenance window
- After security news breaks and you want to know "are we affected?"
- When starting work on a project that's been dormant for a while

## Scan Categories

| Category | What to check | Primary sources |
|----------|--------------|-----------------|
| Security | CVEs/advisories for your actual dependencies | OSV.dev, GitHub Advisories, NVD, RustSec, PyPA |
| API changes | Breaking changes in SDKs/APIs the project calls | Vendor changelogs, release notes |
| Dependencies | Major-version releases, deprecations, EOL notices | PyPI, npm, crates.io registries |
| Research | New techniques relevant to what the project does | arXiv, vendor engineering blogs |

## Workflow

Follow `prompts/scan.md`. Quick summary:

1. **Inventory** — read the project's manifests (requirements.txt, package.json,
   Cargo.toml, go.mod, ...) to build the real dependency list with pinned versions
2. **Sweep** — check each category against the sources above, scoped to that inventory
3. **Filter** — keep only findings that actually affect the versions in use
4. **Report** — severity-ranked markdown report with concrete remediation steps

## Output

A markdown report (printed, or written to a file if the user asks) with sections:
Critical / High / Notable / Informational. Every finding cites its source URL and
names the affected file (e.g. `requirements.txt: aiohttp 3.9.1 → CVE-2024-XXXX,
fixed in 3.9.4`).
