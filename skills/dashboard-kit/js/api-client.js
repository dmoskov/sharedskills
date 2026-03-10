/**
 * DashboardAPIClient - Unified API client with retry logic, timeouts, and deduplication
 *
 * Features:
 * - Automatic retry with exponential backoff
 * - Request timeout (configurable, default 30s)
 * - Request deduplication (prevent duplicate in-flight requests)
 * - Centralized error notification
 * - Request cancellation on page navigation
 * - Performance timing for monitoring
 * - Data freshness metadata tracking and exposure
 */

class DashboardAPIClient {
    constructor(options = {}) {
        this.config = {
            maxAttempts: options.maxAttempts || 3,
            initialDelayMs: options.initialDelayMs || 1000,
            maxDelayMs: options.maxDelayMs || 8000,
            backoffMultiplier: options.backoffMultiplier || 2,
            timeoutMs: options.timeoutMs || 30000,
            enableDeduplication: options.enableDeduplication !== false,
            enablePerformanceLogging: options.enablePerformanceLogging !== false,
            onError: options.onError || null,
            logPrefix: options.logPrefix || '[API]',
            onFreshnessUpdate: options.onFreshnessUpdate || null  // Callback for freshness updates
        };

        // Track in-flight requests for deduplication
        this.inFlightRequests = new Map();

        // Track active AbortControllers for cleanup
        this.activeControllers = new Map();

        // Track freshness metadata per endpoint
        this.freshnessMetadata = new Map();

        // Bind methods
        this.fetch = this.fetch.bind(this);
        this.cancelAll = this.cancelAll.bind(this);

        // Cancel requests on page navigation
        if (typeof window !== 'undefined') {
            window.addEventListener('beforeunload', () => this.cancelAll());
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'hidden') {
                    // Optionally cancel long-running requests when page is hidden
                    // this.cancelAll();
                }
            });
        }
    }

    /**
     * Generate a cache key for request deduplication
     */
    _getRequestKey(url, options = {}) {
        const method = options.method || 'GET';
        const body = options.body || '';
        return `${method}:${url}:${body}`;
    }

    /**
     * Check if an error should trigger a retry
     */
    _isRetryableError(error) {
        const message = error.message || String(error);

        // Non-retryable HTTP status codes
        const nonRetryableCodes = ['401', '403', '404', '422'];
        if (nonRetryableCodes.some(code => message.includes(`HTTP ${code}`))) {
            return false;
        }

        // AbortError from user cancellation should not retry
        if (error.name === 'AbortError' && error.message === 'User cancelled') {
            return false;
        }

        return true;
    }

    /**
     * Calculate delay for next retry attempt using exponential backoff
     */
    _calculateRetryDelay(attempt) {
        const delay = this.config.initialDelayMs *
            Math.pow(this.config.backoffMultiplier, attempt - 1);
        return Math.min(delay, this.config.maxDelayMs);
    }

    /**
     * Convert error to user-friendly message
     */
    getUserFriendlyError(error) {
        const message = error.message || String(error);

        // Network errors
        if (error.name === 'AbortError' || message.includes('aborted')) {
            if (message === 'User cancelled') {
                return 'Request was cancelled.';
            }
            return 'Request timed out. The server took too long to respond.';
        }
        if (message.includes('Failed to fetch') || message.includes('NetworkError')) {
            return 'Network error. Please check your internet connection and try again.';
        }

        // HTTP errors
        if (message.includes('HTTP 401')) {
            return 'Authentication required. Please refresh the page and try again.';
        }
        if (message.includes('HTTP 403')) {
            return 'Access denied. You do not have permission to view this data.';
        }
        if (message.includes('HTTP 404')) {
            return 'Data not found. The requested resource does not exist.';
        }
        if (message.includes('HTTP 422')) {
            return 'Invalid request. Please check the parameters and try again.';
        }
        if (message.includes('HTTP 500')) {
            return 'Server error. Please try again in a few moments.';
        }
        if (message.includes('HTTP 502')) {
            return 'Bad gateway. The server is temporarily unavailable.';
        }
        if (message.includes('HTTP 503')) {
            return 'Service temporarily unavailable. Please try again later.';
        }
        if (message.includes('HTTP 504')) {
            return 'Gateway timeout. The server is taking too long to respond.';
        }

        // JSON parsing errors
        if (message.includes('JSON') || message.includes('Unexpected token')) {
            return 'Invalid server response. Please try refreshing the page.';
        }

        // Default error with original message
        return `Error: ${message}`;
    }

    /**
     * Log with configured prefix
     */
    _log(level, ...args) {
        const logFn = level === 'error' ? console.error : console.log;
        logFn(this.config.logPrefix, ...args);
    }

    /**
     * Main fetch method with retry logic, timeout, and deduplication
     */
    async fetch(url, options = {}) {
        const requestKey = this._getRequestKey(url, options);
        const startTime = performance.now();

        // Request deduplication
        if (this.config.enableDeduplication && this.inFlightRequests.has(requestKey)) {
            this._log('log', `Reusing in-flight request: ${url}`);
            return this.inFlightRequests.get(requestKey);
        }

        const fetchPromise = this._fetchWithRetry(url, options, 1, startTime);

        // Track in-flight request
        if (this.config.enableDeduplication) {
            this.inFlightRequests.set(requestKey, fetchPromise);
            fetchPromise.finally(() => {
                this.inFlightRequests.delete(requestKey);
            });
        }

        return fetchPromise;
    }

    /**
     * Internal retry implementation
     */
    async _fetchWithRetry(url, options = {}, attempt = 1, startTime) {
        const requestKey = this._getRequestKey(url, options);
        const controller = new AbortController();
        const timeoutMs = options.timeout || this.config.timeoutMs;

        // Track controller for cancellation
        this.activeControllers.set(requestKey, controller);

        // Set up timeout
        const timeoutId = setTimeout(() => {
            controller.abort();
        }, timeoutMs);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });

            clearTimeout(timeoutId);
            this.activeControllers.delete(requestKey);

            // Log performance
            if (this.config.enablePerformanceLogging) {
                const duration = performance.now() - startTime;
                this._log('log', `Request completed in ${duration.toFixed(0)}ms: ${url}`);
            }

            // Check for HTTP errors
            if (!response.ok) {
                const errorText = await response.text().catch(() => 'Unknown error');
                throw new Error(`HTTP ${response.status}: ${response.statusText}. ${errorText}`);
            }

            const data = await response.json();

            // Check for application-level errors
            if (data.error) {
                throw new Error(data.error);
            }

            // Extract and track freshness metadata if present
            if (data._metadata) {
                this._trackFreshnessMetadata(url, data._metadata);
            }

            // Update data source indicator with response metadata
            if (typeof dataSourceIndicator !== 'undefined') {
                dataSourceIndicator.updateFromResponse(url, data);
            }

            // Also notify data freshness monitor if available
            if (typeof dataFreshnessMonitor !== 'undefined' && data._metadata) {
                const timestamp = data._metadata.data_source_timestamp
                    ? new Date(data._metadata.data_source_timestamp).getTime()
                    : Date.now();
                dataFreshnessMonitor.trackApiResponse(url, {
                    meta: {
                        fetched_at: data._metadata.data_source_timestamp,
                        data_source: data._metadata.freshness_status === 'critical' ? 'stale' : 'fresh',
                        cache_age_seconds: data._metadata.data_age_seconds
                    }
                });
            }

            // Handle standard API response structure: {data: {...}, meta: {...}}
            // Unwrap the data field and attach metadata for consumer access
            if (data && typeof data === 'object' && 'data' in data && 'meta' in data) {
                const unwrapped = data.data;
                // Attach metadata to unwrapped data for components that need it
                // Only attach if meta is not empty or if it has any properties
                if (unwrapped && typeof unwrapped === 'object' && data.meta && Object.keys(data.meta).length > 0) {
                    unwrapped._metadata = data.meta;
                }
                return unwrapped;
            }

            return data;

        } catch (error) {
            clearTimeout(timeoutId);
            this.activeControllers.delete(requestKey);

            // Update data source indicator with error
            if (typeof dataSourceIndicator !== 'undefined') {
                dataSourceIndicator.setError(url);
            }

            this._log('error', `Fetch attempt ${attempt}/${this.config.maxAttempts} failed:`, error.message);

            // Check if we should retry
            if (!this._isRetryableError(error) || attempt >= this.config.maxAttempts) {
                // Call error callback if provided
                if (this.config.onError) {
                    this.config.onError(error, url);
                }
                throw error;
            }

            // Calculate delay with exponential backoff
            const delay = this._calculateRetryDelay(attempt);
            this._log('log', `Retrying in ${delay}ms...`);

            await new Promise(resolve => setTimeout(resolve, delay));

            // Retry
            return this._fetchWithRetry(url, options, attempt + 1, startTime);
        }
    }

    /**
     * Fetch multiple URLs in parallel with individual error handling
     */
    async fetchAll(requests, options = {}) {
        const { failFast = false } = options;
        const startTime = performance.now();

        const promises = requests.map(req => {
            const url = typeof req === 'string' ? req : req.url;
            const reqOptions = typeof req === 'string' ? {} : req.options;
            return this.fetch(url, reqOptions).catch(error => {
                if (failFast) throw error;
                return { error, url };
            });
        });

        const results = await Promise.all(promises);

        if (this.config.enablePerformanceLogging) {
            const duration = performance.now() - startTime;
            this._log('log', `Parallel requests completed in ${duration.toFixed(0)}ms`);
        }

        return results;
    }

    /**
     * Cancel a specific request
     */
    cancel(url, options = {}) {
        const requestKey = this._getRequestKey(url, options);
        const controller = this.activeControllers.get(requestKey);
        if (controller) {
            const error = new Error('User cancelled');
            error.name = 'AbortError';
            controller.abort();
            this.activeControllers.delete(requestKey);
            this.inFlightRequests.delete(requestKey);
            return true;
        }
        return false;
    }

    /**
     * Cancel all active requests
     */
    cancelAll() {
        this._log('log', `Cancelling ${this.activeControllers.size} active requests`);
        this.activeControllers.forEach((controller, key) => {
            controller.abort();
        });
        this.activeControllers.clear();
        this.inFlightRequests.clear();
    }

    /**
     * Get count of active requests
     */
    getActiveRequestCount() {
        return this.activeControllers.size;
    }

    /**
     * Create a scoped client with a different configuration
     */
    withConfig(overrides) {
        return new DashboardAPIClient({
            ...this.config,
            ...overrides
        });
    }

    /**
     * Track freshness metadata from API response
     * @param {string} url - The API endpoint URL
     * @param {Object} metadata - The _metadata object from the response
     */
    _trackFreshnessMetadata(url, metadata) {
        const normalizedUrl = this._normalizeEndpoint(url);
        this.freshnessMetadata.set(normalizedUrl, {
            ...metadata,
            receivedAt: new Date().toISOString()
        });

        // Call the callback if provided
        if (this.config.onFreshnessUpdate) {
            this.config.onFreshnessUpdate(normalizedUrl, metadata);
        }
    }

    /**
     * Normalize endpoint URL for consistent tracking
     * Removes query parameters for grouping
     */
    _normalizeEndpoint(url) {
        try {
            const urlObj = new URL(url, window.location.origin);
            return urlObj.pathname;
        } catch (e) {
            return url.split('?')[0];
        }
    }

    /**
     * Get freshness metadata for a specific endpoint
     * @param {string} url - The API endpoint URL
     * @returns {Object|null} - The freshness metadata or null if not tracked
     */
    getFreshnessMetadata(url) {
        const normalizedUrl = this._normalizeEndpoint(url);
        return this.freshnessMetadata.get(normalizedUrl) || null;
    }

    /**
     * Get all tracked freshness metadata
     * @returns {Object} - Map of endpoint -> metadata
     */
    getAllFreshnessMetadata() {
        const result = {};
        this.freshnessMetadata.forEach((value, key) => {
            result[key] = value;
        });
        return result;
    }

    /**
     * Get freshness status summary across all endpoints
     * @returns {Object} - Summary with counts and oldest data
     */
    getFreshnessSummary() {
        let totalEndpoints = 0;
        let freshCount = 0;
        let staleCount = 0;
        let criticalCount = 0;
        let oldestTimestamp = null;
        let oldestEndpoint = null;

        this.freshnessMetadata.forEach((metadata, endpoint) => {
            totalEndpoints++;

            switch (metadata.freshness_status) {
                case 'fresh':
                    freshCount++;
                    break;
                case 'stale':
                    staleCount++;
                    break;
                case 'critical':
                    criticalCount++;
                    break;
            }

            if (metadata.data_source_timestamp) {
                const ts = new Date(metadata.data_source_timestamp);
                if (!oldestTimestamp || ts < oldestTimestamp) {
                    oldestTimestamp = ts;
                    oldestEndpoint = endpoint;
                }
            }
        });

        return {
            totalEndpoints,
            freshCount,
            staleCount,
            criticalCount,
            oldestTimestamp: oldestTimestamp ? oldestTimestamp.toISOString() : null,
            oldestEndpoint,
            overallStatus: criticalCount > 0 ? 'critical' : (staleCount > 0 ? 'stale' : 'fresh')
        };
    }

    /**
     * Check if any endpoint has stale or critical data
     * @returns {boolean} - True if any data is stale or critical
     */
    hasStaleData() {
        for (const [, metadata] of this.freshnessMetadata) {
            if (metadata.freshness_status === 'stale' || metadata.freshness_status === 'critical') {
                return true;
            }
        }
        return false;
    }

    /**
     * Clear tracked freshness metadata
     */
    clearFreshnessMetadata() {
        this.freshnessMetadata.clear();
    }

    /**
     * Check if a response is a structured error response
     * @param {*} response - Response to check
     * @returns {boolean} True if response is an error
     */
    static isErrorResponse(response) {
        if (typeof ErrorResponse !== 'undefined' && ErrorResponse.isError) {
            return ErrorResponse.isError(response);
        }
        return response && typeof response === 'object' && response.error === true && response.code;
    }

    /**
     * Get error message from a response (handles both normal errors and structured error responses)
     * @param {*} errorOrResponse - Error or response to get message from
     * @returns {string} User-friendly error message
     */
    getErrorMessage(errorOrResponse) {
        // Check for structured error response
        if (DashboardAPIClient.isErrorResponse(errorOrResponse)) {
            return errorOrResponse.message || 'An error occurred';
        }
        // Check for Error object
        if (errorOrResponse instanceof Error) {
            return this.getUserFriendlyError(errorOrResponse);
        }
        // Fallback
        return String(errorOrResponse);
    }

    /**
     * Check if an error or response is retryable
     * @param {*} errorOrResponse - Error or response to check
     * @returns {boolean} True if retryable
     */
    isRetryable(errorOrResponse) {
        // Check for structured error response
        if (DashboardAPIClient.isErrorResponse(errorOrResponse)) {
            return errorOrResponse.retryable === true;
        }
        // Check for Error object
        if (errorOrResponse instanceof Error) {
            return this._isRetryableError(errorOrResponse);
        }
        return false;
    }
}

// Create a default singleton instance
const dashboardAPI = new DashboardAPIClient({
    logPrefix: '[DashboardAPI]'
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DashboardAPIClient, dashboardAPI };
}
