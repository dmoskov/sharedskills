/**
 * BaseDashboardController - Shared initialization and utilities for all dashboards
 *
 * Reduces code duplication by providing:
 * - Standard event listener setup
 * - Freshness tracking initialization
 * - Widget registration helpers
 * - Common refresh patterns
 *
 * Usage:
 *   class EngagementDashboard extends BaseDashboardController {
 *     constructor() {
 *       super({
 *         refreshCallback: () => this.refreshData(),
 *         widgets: ['engagement-metrics', 'engagement-hourly', 'engagement-viral']
 *       });
 *     }
 *
 *     async refreshData() { ... }
 *   }
 */
class BaseDashboardController {
    constructor(config = {}) {
        this.config = {
            refreshCallback: config.refreshCallback || null,
            widgets: config.widgets || [],
            timeRangeSelector: config.timeRangeSelector || '#timeRange',
            refreshButton: config.refreshButton || '#refreshBtn',
            autoRefresh: config.autoRefresh !== false,
            autoRefreshInterval: config.autoRefreshInterval || 30000
        };

        this.autoRefreshTimer = null;
        this.isRefreshing = false;
        this.freshnessTracker = null;
    }

    /**
     * Initialize the dashboard - call this from window.addEventListener('load')
     */
    async init() {
        this.initEventListeners();
        this.initFreshnessTracking();

        if (this.config.refreshCallback) {
            await this.refresh();
        }

        if (this.config.autoRefresh) {
            this.startAutoRefresh();
        }
    }

    /**
     * Set up standard event listeners (refresh button, time range selector)
     */
    initEventListeners() {
        const refreshBtn = document.querySelector(this.config.refreshButton);
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refresh());
        }

        const timeRangeSelect = document.querySelector(this.config.timeRangeSelector);
        if (timeRangeSelect) {
            timeRangeSelect.addEventListener('change', (e) => {
                if (typeof window.currentTimeRange !== 'undefined') {
                    window.currentTimeRange = e.target.value;
                }
                this.refresh();
            });
        }
    }

    /**
     * Initialize freshness tracking for registered widgets
     */
    initFreshnessTracking() {
        if (typeof initFreshnessTracker !== 'function') {
            console.warn('[BaseDashboard] Freshness tracker not available');
            return;
        }

        initFreshnessTracker();
        this.freshnessTracker = typeof getFreshnessTracker === 'function' ? getFreshnessTracker() : null;

        // Register all configured widgets
        this.config.widgets.forEach(widgetId => {
            this.registerWidget(widgetId);
        });
    }

    /**
     * Register a widget for freshness tracking
     * @param {string} widgetId - Widget identifier
     * @param {Object} options - Registration options (selector, insertPosition, etc.)
     */
    registerWidget(widgetId, options = {}) {
        if (!this.freshnessTracker) return;

        const selector = options.selector || `#${widgetId}`;
        const element = document.querySelector(selector);

        if (!element) {
            console.warn(`[BaseDashboard] Widget element not found: ${selector}`);
            return;
        }

        // Determine container based on widget type
        let container = element;
        if (options.containerSelector) {
            container = element.querySelector(options.containerSelector) || element.closest(options.containerSelector);
        } else if (element.tagName === 'CANVAS') {
            container = element.closest('.chart-container');
        }

        if (container) {
            this.freshnessTracker.register(widgetId, container, {
                insertPosition: options.insertPosition || 'inside'
            });
        }
    }

    /**
     * Mark a widget as fresh (updated with new data)
     */
    markWidgetFresh(widgetId) {
        if (typeof updateFreshness === 'function') {
            updateFreshness(widgetId);
        }
    }

    /**
     * Mark all registered widgets as fresh
     */
    markAllWidgetsFresh() {
        this.config.widgets.forEach(widgetId => this.markWidgetFresh(widgetId));
    }

    /**
     * Refresh dashboard data
     */
    async refresh() {
        if (this.isRefreshing) {
            console.log('[BaseDashboard] Refresh already in progress');
            return;
        }

        this.isRefreshing = true;

        try {
            if (this.config.refreshCallback) {
                await this.config.refreshCallback();
            }

            // Update last update timestamp
            if (typeof updateLastUpdate === 'function') {
                updateLastUpdate();
            }
        } catch (error) {
            console.error('[BaseDashboard] Refresh failed:', error);
            if (typeof showError === 'function') {
                showError(error.message || 'Failed to refresh dashboard');
            }
        } finally {
            this.isRefreshing = false;
        }
    }

    /**
     * Start auto-refresh timer
     */
    startAutoRefresh() {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
        }

        this.autoRefreshTimer = setInterval(() => {
            this.refresh();
        }, this.config.autoRefreshInterval);

        console.log(`[BaseDashboard] Auto-refresh started (${this.config.autoRefreshInterval}ms)`);
    }

    /**
     * Stop auto-refresh timer
     */
    stopAutoRefresh() {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
            this.autoRefreshTimer = null;
            console.log('[BaseDashboard] Auto-refresh stopped');
        }
    }

    /**
     * Clean up resources
     */
    destroy() {
        this.stopAutoRefresh();
        this.freshnessTracker = null;
    }
}

// Make available globally
if (typeof window !== 'undefined') {
    window.BaseDashboardController = BaseDashboardController;
}
