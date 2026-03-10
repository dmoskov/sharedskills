# Dashboard Kit

Shared dashboard infrastructure for building analytics dashboards. Extracted from the [pan](https://github.com/dmoskov/pan) project's production dashboard system.

## Files

### CSS
- **`css/dashboard-common.css`** — Core styling: CSS variables, layout, components, dark mode, responsive
- **`css/dashboard-responsive.css`** — Mobile/tablet responsive breakpoints
- **`css/accessibility.css`** — WCAG 2.1 AA accessibility patterns

### JavaScript
- **`js/api-client.js`** — `DashboardAPIClient` with retry, deduplication, timeout, freshness tracking
- **`js/dashboard-base.js`** — `BaseDashboardController` base class for dashboard pages
- **`js/d3-utils.js`** — D3.js visualization utilities (SVG, zoom, tooltips, force simulation, scales)
- **`js/data-freshness-monitor.js`** — Pipeline health monitoring with auto-injected warning banner
- **`js/data-validator.js`** — Schema-based API response validation

## Usage

### As a git submodule

```bash
git submodule add https://github.com/dmoskov/sharedskills.git ai-dev-tools
```

Then symlink or reference files from `ai-dev-tools/skills/dashboard-kit/`.

### Configuration

Override defaults via `window.dashboardKitConfig` before scripts load:

```html
<script>
  window.dashboardKitConfig = {
    freshnessMonitor: {
      healthEndpoint: '/api/my-health-endpoint',
      pipelineStatusHref: '/my-pipeline-page.html'
    }
  };
</script>
```

## Integration Pattern

```html
<head>
  <link rel="stylesheet" href="/path/to/dashboard-kit/css/dashboard-common.css">
  <link rel="stylesheet" href="/path/to/dashboard-kit/css/dashboard-responsive.css">
</head>
<body>
  <!-- Dashboard content -->
  <script src="/path/to/dashboard-kit/js/api-client.js"></script>
  <script src="/path/to/dashboard-kit/js/data-freshness-monitor.js"></script>
  <script src="/path/to/dashboard-kit/js/data-validator.js"></script>
  <script src="/path/to/dashboard-kit/js/dashboard-base.js"></script>
</body>
```
