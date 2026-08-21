# Environmental Scan Prompt

You are performing an environmental scan: find external developments (vulnerabilities,
breaking changes, notable releases, relevant research) that affect THIS project, and
report them ranked by severity. Ground every claim in a source you actually fetched —
never report a CVE or release from memory alone.

## Step 1: Inventory the Project

Build the real exposure surface before searching anything:

1. Find dependency manifests: `requirements.txt`, `pyproject.toml`, `package.json`,
   `package-lock.json`, `Cargo.toml`, `go.mod`, `Gemfile`, `Dockerfile` (base images),
   `.github/workflows/*.yml` (actions used)
2. Extract each dependency with its pinned or resolved version
3. Note the external APIs/services the code calls (grep for SDK imports and API URLs)
4. Note language/runtime versions

Skip anything not actually used — scanning imaginary dependencies produces noise.

## Step 2: Sweep by Category

For each category, scope queries to the inventory from Step 1.

### Security (highest priority)
- Query OSV.dev for each significant dependency: `https://api.osv.dev/v1/query`
  (POST with `{"package": {"name": "...", "ecosystem": "PyPI|npm|crates.io|Go"}, "version": "..."}`)
  — or fetch `https://osv.dev/list?q=<package>` / GitHub Advisories
- For base images and runtimes, search "<name> <version> CVE <current year>"
- Record: CVE/advisory ID, affected version range, fixed version, exploitability notes

### API / SDK Changes
- For each external API or SDK in use, fetch its changelog or releases page
- Look for: breaking changes, deprecation notices, auth changes, rate-limit changes
- Only flag items affecting endpoints/features the project actually uses

### Dependency Releases
- For core dependencies (direct, heavily used), check the registry for:
  major versions released since the pinned version, EOL/maintenance-mode
  announcements, and migration guides

### Research / Ecosystem (optional, judgment call)
- Only if relevant to the project's domain: search arXiv or vendor engineering blogs
  for techniques directly applicable to what this project does
- Keep to 2-3 genuinely useful items; this section is easy to fill with noise

## Step 3: Filter to Actual Impact

Discard findings that don't apply:
- CVE affects a version range the project isn't in
- CVE is in a feature/module the project doesn't use (say so explicitly if you keep it)
- Breaking change in an API surface the project doesn't call

When you can't confirm whether a finding applies, KEEP it and mark it "unconfirmed —
verify" — for security findings, fail open, not closed.

## Step 4: Report

Produce a markdown report:

```markdown
# Environmental Scan: <project> — <date>

## Summary
<2-3 sentences: overall posture, count by severity, single most urgent item>

## Critical — act now
- **<ID/title>** — <affected dep + version> → <impact>. Fix: <upgrade to X / change Y>. [source](url)

## High — schedule this week
...

## Notable — plan for
<major versions, deprecations, EOL timelines>

## Informational
<relevant releases/research, one line each>

## Not affected (checked and cleared)
<top deps checked with no applicable findings — so the reader knows coverage>
```

Rules:
- Every finding: source URL + affected file/dependency + concrete remediation
- The "Not affected" section is mandatory — a scan that only lists problems hides
  its own coverage
- If the user wants it saved, write to `docs/environmental-scan-<date>.md` (or where
  they specify); otherwise print it
- Offer (don't auto-file) follow-up tasks for Critical/High items
