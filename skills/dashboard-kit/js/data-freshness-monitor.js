/**
 * @fileoverview Data Freshness Monitor
 * @module data-freshness-monitor
 *
 * Monitors data freshness across the dashboard and displays warnings when data may be stale.
 * Integrates with:
 * - FreshnessTracker for per-widget freshness indicators
 * - WebSocket status for connection monitoring
 * - Pipeline health API for service status
 *
 * Features:
 * - Auto-injects warning banner into nav-header
 * - Monitors API response metadata for staleness
 * - Shows warnings when data exceeds freshness thresholds
 * - Detects pipeline degradation from health endpoint
 * - Provides global data freshness status
 *
 * Usage:
 *   <script src="/dashboard/js/data-freshness-monitor.js"></script>
 *   // Monitor auto-initializes on DOM ready
 */

(function () {
    'use strict';

    // Configuration — override via window.dashboardKitConfig.freshnessMonitor
    const userConfig = (window.dashboardKitConfig && window.dashboardKitConfig.freshnessMonitor) || {};
    const CONFIG = Object.assign({
        // Thresholds in milliseconds
        warningThresholdMs: 5 * 60 * 1000,    // 5 minutes - show warning
        criticalThresholdMs: 30 * 60 * 1000,  // 30 minutes - show critical warning
        staleThresholdMs: 60 * 60 * 1000,     // 1 hour - data is stale

        // Health check interval
        healthCheckIntervalMs: 30000,  // Check pipeline health every 30 seconds

        // Banner container ID
        bannerId: 'data-freshness-warning-banner',

        // Health endpoint
        healthEndpoint: '/api/collection-health',

        // Pipeline status link (shown in warning banner)
        pipelineStatusHref: '/dashboard/pipeline_health.html',

        // Enable/disable features
        enableBanner: true,
        enableHealthMonitor: true,
        enableApiMetadataTracking: true
    }, userConfig);

    // State tracking
    let bannerElement = null;
    let healthCheckTimer = null;
    let lastHealthCheck = null;
    let boundHandlers = {};
    let currentState = {
        pipelineHealthy: true,
        pipelineStatus: 'unknown',
        servicesDown: [],
        oldestDataTimestamp: null,
        apiResponseTimestamps: new Map(),
        wsConnected: false,
        wsState: 'disconnected'
    };

    // Logger
    const log = typeof PanLogger !== 'undefined' ? PanLogger.getLogger('FreshnessMonitor') : {
        debug: (...args) => console.debug('[FreshnessMonitor]', ...args),
        info: (...args) => console.log('[FreshnessMonitor]', ...args),
        warn: (...args) => console.warn('[FreshnessMonitor]', ...args),
        error: (...args) => console.error('[FreshnessMonitor]', ...args)
    };

    /**
     * Create the warning banner element
     * @returns {HTMLElement}
     */
    function createBannerElement() {
        const banner = document.createElement('div');
        banner.id = CONFIG.bannerId;
        banner.className = 'data-freshness-warning-banner hidden';
        banner.setAttribute('role', 'alert');
        banner.setAttribute('aria-live', 'polite');

        banner.innerHTML = `
            <span class="data-freshness-warning-icon" aria-hidden="true">⚠️</span>
            <span class="data-freshness-warning-text">
                Data may be stale. Some services are experiencing issues.
            </span>
            <a href="${CONFIG.pipelineStatusHref}" class="data-freshness-warning-link">
                View Pipeline Status
            </a>
            <button class="data-freshness-warning-dismiss" aria-label="Dismiss warning" style="
                background: none;
                border: none;
                font-size: 18px;
                cursor: pointer;
                padding: 0 4px;
                color: inherit;
                opacity: 0.7;
            ">×</button>
        `;

        return banner;
    }

    /**
     * Inject the banner into the page header
     */
    function injectBanner() {
        if (!CONFIG.enableBanner) return;

        // Check if already exists
        if (document.getElementById(CONFIG.bannerId)) {
            bannerElement = document.getElementById(CONFIG.bannerId);
            return;
        }

        // Create banner
        bannerElement = createBannerElement();

        // Insert at the top of body, before nav-header
        const navHeader = document.querySelector('.nav-header');
        if (navHeader) {
            navHeader.parentNode.insertBefore(bannerElement, navHeader);
        } else {
            document.body.insertBefore(bannerElement, document.body.firstChild);
        }

        // Add dismiss handler
        const dismissBtn = bannerElement.querySelector('.data-freshness-warning-dismiss');
        if (dismissBtn) {
            dismissBtn.addEventListener('click', function () {
                hideBanner();
                // Store dismissal in session storage (will reappear on page reload)
                sessionStorage.setItem('freshnessWarningDismissed', Date.now().toString());
            });
        }

        log.debug('Banner injected into page');
    }

    /**
     * Show the warning banner
     * @param {Object} options - Display options
     * @param {boolean} options.critical - Show critical (red) styling
     * @param {string} options.message - Custom message text
     * @param {string[]} options.servicesDown - List of services that are down
     */
    function showBanner(options = {}) {
        if (!bannerElement) return;

        // Check if user dismissed recently (within last 5 minutes)
        const dismissedAt = sessionStorage.getItem('freshnessWarningDismissed');
        if (dismissedAt) {
            const dismissedMs = Date.now() - parseInt(dismissedAt, 10);
            if (dismissedMs < 5 * 60 * 1000) {
                log.debug('Banner dismissed recently, skipping display');
                return;
            }
            sessionStorage.removeItem('freshnessWarningDismissed');
        }

        // Update styling
        if (options.critical) {
            bannerElement.classList.add('critical');
        } else {
            bannerElement.classList.remove('critical');
        }

        // Update message
        const textEl = bannerElement.querySelector('.data-freshness-warning-text');
        if (textEl) {
            let message = options.message || 'Data may be stale. Some services are experiencing issues.';

            // Add service-specific info
            if (options.servicesDown && options.servicesDown.length > 0) {
                message = `${message} Affected: ${options.servicesDown.join(', ')}.`;
            }

            textEl.textContent = message;
        }

        // Update icon
        const iconEl = bannerElement.querySelector('.data-freshness-warning-icon');
        if (iconEl) {
            iconEl.textContent = options.critical ? '🚨' : '⚠️';
        }

        // Show banner
        bannerElement.classList.remove('hidden');
        bannerElement.setAttribute('aria-hidden', 'false');

        log.info('Banner shown', { critical: options.critical, servicesDown: options.servicesDown });
    }

    /**
     * Hide the warning banner
     */
    function hideBanner() {
        if (!bannerElement) return;

        bannerElement.classList.add('hidden');
        bannerElement.setAttribute('aria-hidden', 'true');
        bannerElement.classList.remove('critical');

        log.debug('Banner hidden');
    }

    /**
     * Check pipeline health status
     */
    async function checkPipelineHealth() {
        if (!CONFIG.enableHealthMonitor) return;

        try {
            const response = await fetch(CONFIG.healthEndpoint, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });

            if (!response.ok) {
                throw new Error(`Health check failed: ${response.status}`);
            }

            let result = await response.json();

            // Handle standardized API response structure
            if (result && typeof result === 'object' && 'data' in result && 'meta' in result) {
                result = result.data;
            }

            lastHealthCheck = Date.now();

            // Process health data
            processHealthData(result);

        } catch (error) {
            log.error('Health check failed', { error: error.message });

            // Assume unhealthy if we can't reach the endpoint
            currentState.pipelineHealthy = false;
            currentState.pipelineStatus = 'unreachable';

            showBanner({
                critical: true,
                message: 'Unable to check pipeline status. Data may be stale.'
            });
        }
    }

    /**
     * Process health data from the API
     * @param {Object} data - Health response data
     */
    function processHealthData(data) {
        // Extract services status
        const services = data.data?.services || data.services || [];
        const servicesDown = [];
        let anyUnhealthy = false;
        let anyWarning = false;

        services.forEach(function (service) {
            if (service.status === 'error' || service.status === 'unhealthy' || service.status === 'critical') {
                servicesDown.push(service.name || service.service_name);
                anyUnhealthy = true;
            } else if (service.status === 'warning' || service.status === 'degraded') {
                anyWarning = true;
            }
        });

        // Update state
        currentState.pipelineHealthy = !anyUnhealthy;
        currentState.servicesDown = servicesDown;

        if (anyUnhealthy) {
            currentState.pipelineStatus = 'unhealthy';
        } else if (anyWarning) {
            currentState.pipelineStatus = 'degraded';
        } else {
            currentState.pipelineStatus = 'healthy';
        }

        // Update banner based on status
        if (anyUnhealthy) {
            showBanner({
                critical: true,
                message: 'Pipeline issues detected. Data may be stale.',
                servicesDown: servicesDown
            });
        } else if (anyWarning) {
            showBanner({
                critical: false,
                message: 'Some services are degraded. Data may be delayed.'
            });
        } else {
            // Check data freshness even if services are healthy
            checkDataFreshness();
        }

        log.debug('Health data processed', { status: currentState.pipelineStatus, servicesDown });
    }

    /**
     * Check overall data freshness from tracked API responses
     */
    function checkDataFreshness() {
        if (!CONFIG.enableApiMetadataTracking) {
            hideBanner();
            return;
        }

        const now = Date.now();
        let oldestTimestamp = null;
        let staleEndpoints = [];

        // Check all tracked API response timestamps
        currentState.apiResponseTimestamps.forEach(function (timestamp, endpoint) {
            const age = now - timestamp;

            if (age > CONFIG.criticalThresholdMs) {
                staleEndpoints.push(endpoint);
            }

            if (oldestTimestamp === null || timestamp < oldestTimestamp) {
                oldestTimestamp = timestamp;
            }
        });

        currentState.oldestDataTimestamp = oldestTimestamp;

        // Determine if we should show warning
        if (staleEndpoints.length > 0) {
            const oldestAge = now - oldestTimestamp;

            if (oldestAge > CONFIG.staleThresholdMs) {
                showBanner({
                    critical: true,
                    message: `Data is over ${Math.round(oldestAge / 60000)} minutes old. Please refresh.`
                });
            } else if (oldestAge > CONFIG.criticalThresholdMs) {
                showBanner({
                    critical: true,
                    message: 'Data may be significantly outdated. Consider refreshing.'
                });
            } else if (oldestAge > CONFIG.warningThresholdMs) {
                showBanner({
                    critical: false,
                    message: 'Data is a few minutes old. Auto-refresh is paused.'
                });
            }
        } else {
            // All data is fresh, hide banner
            hideBanner();
        }
    }

    /**
     * Track API response metadata
     * Called from fetchAPI or similar functions to track data freshness
     * @param {string} endpoint - API endpoint
     * @param {Object} response - API response with meta block
     */
    function trackApiResponse(endpoint, response) {
        if (!CONFIG.enableApiMetadataTracking) return;

        // Extract timestamp from response metadata
        let timestamp = Date.now();

        if (response && response.meta) {
            if (response.meta.fetched_at) {
                timestamp = new Date(response.meta.fetched_at).getTime();
            }

            // Check if data source indicates staleness
            if (response.meta.data_source === 'stale') {
                log.warn('Stale data detected from API', { endpoint });
            }

            // Track cache age
            if (response.meta.cache_age_seconds && response.meta.cache_age_seconds > 300) {
                timestamp = Date.now() - (response.meta.cache_age_seconds * 1000);
            }
        }

        currentState.apiResponseTimestamps.set(endpoint, timestamp);

        log.debug('API response tracked', { endpoint, timestamp: new Date(timestamp).toISOString() });

        // Re-check freshness after tracking new response
        if (currentState.pipelineHealthy) {
            checkDataFreshness();
        }
    }

    /**
     * Handle WebSocket state changes
     * @param {string} state - New WebSocket state
     */
    function handleWsStateChange(state) {
        currentState.wsState = state;
        currentState.wsConnected = (state === 'websocket' || state === 'connected');

        // If WebSocket disconnected and we're not polling, show warning
        if (!currentState.wsConnected && state !== 'polling') {
            // Don't show banner immediately - wait for data staleness
            log.debug('WebSocket disconnected', { state });
        }
    }

    /**
     * Get current freshness status
     * @returns {Object} Current status object
     */
    function getStatus() {
        return {
            pipelineHealthy: currentState.pipelineHealthy,
            pipelineStatus: currentState.pipelineStatus,
            servicesDown: [...currentState.servicesDown],
            wsConnected: currentState.wsConnected,
            wsState: currentState.wsState,
            oldestDataTimestamp: currentState.oldestDataTimestamp,
            dataAge: currentState.oldestDataTimestamp
                ? Date.now() - currentState.oldestDataTimestamp
                : null,
            lastHealthCheck: lastHealthCheck
        };
    }

    /**
     * Force a health check
     */
    function forceHealthCheck() {
        checkPipelineHealth();
    }

    /**
     * Start health monitoring
     */
    function startMonitoring() {
        if (healthCheckTimer) {
            clearInterval(healthCheckTimer);
        }

        // Initial health check
        checkPipelineHealth();

        // Schedule periodic checks
        healthCheckTimer = setInterval(checkPipelineHealth, CONFIG.healthCheckIntervalMs);

        log.info('Health monitoring started', { intervalMs: CONFIG.healthCheckIntervalMs });
    }

    /**
     * Stop health monitoring
     */
    function stopMonitoring() {
        if (healthCheckTimer) {
            clearInterval(healthCheckTimer);
            healthCheckTimer = null;
        }

        log.info('Health monitoring stopped');
    }

    /**
     * Initialize the freshness monitor
     */
    function init() {
        // Inject banner element
        injectBanner();

        // Start health monitoring
        startMonitoring();

        // Listen for WebSocket state changes (store reference for cleanup)
        boundHandlers.realtimeStateChange = function (e) {
            if (e.detail && e.detail.state) {
                handleWsStateChange(e.detail.state);
            }
        };
        window.addEventListener('realtimeStateChange', boundHandlers.realtimeStateChange);

        // Listen for visibility changes - pause monitoring when tab is hidden (store reference for cleanup)
        boundHandlers.visibilityChange = function () {
            if (document.hidden) {
                stopMonitoring();
            } else {
                startMonitoring();
            }
        };
        document.addEventListener('visibilitychange', boundHandlers.visibilityChange);

        log.info('Data freshness monitor initialized');
    }

    /**
     * Cleanup on page unload
     */
    function cleanup() {
        stopMonitoring();
        if (boundHandlers.realtimeStateChange) {
            window.removeEventListener('realtimeStateChange', boundHandlers.realtimeStateChange);
        }
        if (boundHandlers.visibilityChange) {
            document.removeEventListener('visibilitychange', boundHandlers.visibilityChange);
        }
        boundHandlers = {};
        if (bannerElement && bannerElement.parentNode) {
            bannerElement.parentNode.removeChild(bannerElement);
        }
    }

    // Expose API globally
    window.dataFreshnessMonitor = {
        init: init,
        cleanup: cleanup,
        getStatus: getStatus,
        trackApiResponse: trackApiResponse,
        forceHealthCheck: forceHealthCheck,
        showBanner: showBanner,
        hideBanner: hideBanner,
        startMonitoring: startMonitoring,
        stopMonitoring: stopMonitoring
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Cleanup on unload
    window.addEventListener('beforeunload', cleanup);

})();
