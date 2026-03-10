/**
 * @fileoverview Data Validator Utility
 * @module data-validator
 *
 * Client-side data validation utility that verifies data meets minimum quality
 * thresholds before rendering visualizations. Prevents users from making
 * decisions based on incomplete or malformed data.
 *
 * Features:
 * - Schema-based validation for dashboard data types
 * - Array, field, range, and type validators
 * - Validation result with errors and warnings
 * - Integration with EmptyState and error display components
 * - Inline warning display support
 *
 * Usage:
 *   import { DataValidator, SCHEMAS } from './data-validator.js';
 *
 *   // Validate data before rendering
 *   const result = DataValidator.validateForView(data, SCHEMAS.posts);
 *   if (!result.valid) {
 *     EmptyState.showError(container, result.errors[0]);
 *     return;
 *   }
 *   if (result.warnings.length > 0) {
 *     showValidationWarnings(container, result.warnings);
 *   }
 *   renderChart(data);
 */

(function(global) {
    'use strict';

    // Logger
    const log = typeof PanLogger !== 'undefined' ? PanLogger.getLogger('DataValidator') : {
        debug: (...args) => console.debug('[DataValidator]', ...args),
        info: (...args) => console.log('[DataValidator]', ...args),
        warn: (...args) => console.warn('[DataValidator]', ...args),
        error: (...args) => console.error('[DataValidator]', ...args)
    };

    /**
     * Validation result object
     * @typedef {Object} ValidationResult
     * @property {boolean} valid - Whether the data passed validation
     * @property {string[]} errors - Critical errors that prevent rendering
     * @property {string[]} warnings - Non-critical issues to display inline
     * @property {Object} metadata - Additional validation metadata
     */

    /**
     * Field definition for schema
     * @typedef {Object} FieldDefinition
     * @property {string} type - Expected type: 'string', 'number', 'boolean', 'array', 'object', 'date'
     * @property {boolean} [required] - Whether field is required
     * @property {number} [min] - Minimum value for numbers, min length for strings/arrays
     * @property {number} [max] - Maximum value for numbers, max length for strings/arrays
     * @property {string} [pattern] - Regex pattern for strings
     * @property {Object} [itemSchema] - Schema for array items
     * @property {Object} [properties] - Schema for object properties
     * @property {*} [default] - Default value if field is missing
     * @property {string} [warnIf] - Condition that triggers a warning: 'empty', 'low', 'high'
     */

    /**
     * Validation schema
     * @typedef {Object} ValidationSchema
     * @property {string} name - Schema name for error messages
     * @property {Object.<string, FieldDefinition>} fields - Field definitions
     * @property {Object} [arrayConfig] - Configuration if validating an array
     * @property {number} [arrayConfig.minLength] - Minimum array length
     * @property {number} [arrayConfig.maxLength] - Maximum array length
     * @property {Object} [arrayConfig.itemSchema] - Schema for array items
     */

    /**
     * Pre-defined validation schemas for dashboard data types
     */
    const SCHEMAS = {
        /**
         * Schema for posts data
         */
        posts: {
            name: 'Posts',
            arrayConfig: {
                minLength: 0,
                warnIfEmpty: true
            },
            itemSchema: {
                fields: {
                    uri: { type: 'string', required: true },
                    content: { type: 'string', required: false },
                    author_did: { type: 'string', required: false },
                    author_handle: { type: 'string', required: false },
                    created_at: { type: 'date', required: false },
                    engagement: {
                        type: 'object',
                        required: false,
                        properties: {
                            likes: { type: 'number', min: 0 },
                            reposts: { type: 'number', min: 0 }
                        }
                    }
                }
            }
        },

        /**
         * Schema for viral posts response
         */
        viralPosts: {
            name: 'Viral Posts',
            fields: {
                viral_posts: {
                    type: 'array',
                    required: true,
                    warnIf: 'empty'
                },
                total_count: { type: 'number', required: false, min: 0 }
            },
            nestedArrays: {
                'viral_posts': {
                    itemSchema: {
                        fields: {
                            uri: { type: 'string', required: true },
                            content: { type: 'string', required: false },
                            metrics: {
                                type: 'object',
                                required: false,
                                properties: {
                                    likes: { type: 'number', min: 0 },
                                    reposts: { type: 'number', min: 0 },
                                    total_engagement: { type: 'number', min: 0 }
                                }
                            }
                        }
                    }
                }
            }
        },

        /**
         * Schema for engagement data
         */
        engagement: {
            name: 'Engagement',
            fields: {
                total_engagements: { type: 'number', required: false, min: 0 },
                likes_count: { type: 'number', required: false, min: 0 },
                reposts_count: { type: 'number', required: false, min: 0 }
            }
        },

        /**
         * Schema for hourly engagement data
         */
        hourlyEngagement: {
            name: 'Hourly Engagement',
            fields: {
                hours: {
                    type: 'array',
                    required: true,
                    minLength: 1
                },
                actions: {
                    type: 'array',
                    required: true,
                    minLength: 1
                }
            }
        },

        /**
         * Schema for themes/topics data
         */
        themes: {
            name: 'Themes',
            fields: {
                topics: {
                    type: 'object',
                    required: false,
                    warnIf: 'empty'
                },
                total_analyzed: { type: 'number', required: false, min: 0 }
            }
        },

        /**
         * Schema for semantic analysis response
         */
        semanticAnalysis: {
            name: 'Semantic Analysis',
            fields: {
                topics: {
                    type: 'object',
                    required: false,
                    warnIf: 'empty'
                },
                language_distribution: {
                    type: 'object',
                    required: false
                },
                total_analyzed: { type: 'number', required: false, min: 0 }
            }
        },

        /**
         * Schema for trending data
         */
        trending: {
            name: 'Trending',
            fields: {
                trending_topics: {
                    type: 'array',
                    required: false,
                    warnIf: 'empty'
                },
                trending_hashtags: {
                    type: 'array',
                    required: false,
                    warnIf: 'empty'
                }
            }
        },

        /**
         * Schema for narratives data
         */
        narratives: {
            name: 'Narratives',
            fields: {
                narratives: {
                    type: 'array',
                    required: false,
                    warnIf: 'empty'
                },
                total_count: { type: 'number', required: false, min: 0 }
            },
            nestedArrays: {
                'narratives': {
                    itemSchema: {
                        fields: {
                            id: { type: 'number', required: true },
                            name: { type: 'string', required: false },
                            post_count: { type: 'number', required: false, min: 0 },
                            confidence: { type: 'number', required: false, min: 0, max: 1 }
                        }
                    }
                }
            }
        },

        /**
         * Schema for stats/overview data
         */
        stats: {
            name: 'Statistics',
            fields: {
                total_posts: { type: 'number', required: false, min: 0 },
                posts_24h: { type: 'number', required: false, min: 0 },
                total_users: { type: 'number', required: false, min: 0 },
                active_users_24h: { type: 'number', required: false, min: 0 }
            }
        },

        /**
         * Schema for network data
         */
        network: {
            name: 'Network',
            fields: {
                nodes: {
                    type: 'array',
                    required: true,
                    minLength: 0,
                    warnIf: 'empty'
                },
                edges: {
                    type: 'array',
                    required: false
                },
                links: {
                    type: 'array',
                    required: false
                }
            },
            nestedArrays: {
                'nodes': {
                    itemSchema: {
                        fields: {
                            id: { type: 'string', required: true }
                        }
                    }
                }
            }
        },

        /**
         * Schema for chart data (generic time series)
         */
        chartData: {
            name: 'Chart Data',
            fields: {
                labels: {
                    type: 'array',
                    required: true,
                    minLength: 1
                },
                datasets: {
                    type: 'array',
                    required: true,
                    minLength: 1
                }
            },
            nestedArrays: {
                'datasets': {
                    itemSchema: {
                        fields: {
                            data: { type: 'array', required: true, minLength: 1 }
                        }
                    }
                }
            }
        },

        /**
         * Schema for health check data
         */
        health: {
            name: 'Health Status',
            fields: {
                status: { type: 'string', required: true },
                services: { type: 'array', required: false }
            }
        }
    };

    /**
     * DataValidator - Main validation utility
     */
    const DataValidator = {
        /**
         * Validate data against a schema
         * @param {*} data - Data to validate
         * @param {ValidationSchema} schema - Schema to validate against
         * @returns {ValidationResult} Validation result
         */
        validateForView(data, schema) {
            const result = {
                valid: true,
                errors: [],
                warnings: [],
                metadata: {
                    schema: schema.name,
                    timestamp: new Date().toISOString(),
                    dataType: typeof data
                }
            };

            // Check for null/undefined data
            if (data === null || data === undefined) {
                result.valid = false;
                result.errors.push(`No ${schema.name} data received`);
                log.warn('Validation failed: null/undefined data', { schema: schema.name });
                return result;
            }

            // Handle array validation at root level
            if (schema.arrayConfig) {
                return this._validateArray(data, schema.arrayConfig, schema.itemSchema, schema.name, result);
            }

            // Validate object fields
            if (schema.fields) {
                this._validateFields(data, schema.fields, '', result);
            }

            // Validate nested arrays
            if (schema.nestedArrays) {
                this._validateNestedArrays(data, schema.nestedArrays, result);
            }

            // Log validation result
            if (!result.valid) {
                log.warn('Validation failed', { schema: schema.name, errors: result.errors });
            } else if (result.warnings.length > 0) {
                log.debug('Validation passed with warnings', { schema: schema.name, warnings: result.warnings });
            }

            return result;
        },

        /**
         * Validate an array value
         * @param {*} value - Value to validate
         * @param {Object} arrayConfig - Array configuration
         * @param {Object} itemSchema - Schema for array items
         * @param {string} fieldName - Field name for error messages
         * @param {ValidationResult} result - Result object to update
         * @returns {ValidationResult} Updated result
         */
        _validateArray(value, arrayConfig, itemSchema, fieldName, result) {
            if (!Array.isArray(value)) {
                result.valid = false;
                result.errors.push(`${fieldName} must be an array`);
                return result;
            }

            result.metadata.arrayLength = value.length;

            // Check minimum length
            if (arrayConfig.minLength !== undefined && value.length < arrayConfig.minLength) {
                result.valid = false;
                result.errors.push(`${fieldName} requires at least ${arrayConfig.minLength} items, got ${value.length}`);
                return result;
            }

            // Check maximum length
            if (arrayConfig.maxLength !== undefined && value.length > arrayConfig.maxLength) {
                result.warnings.push(`${fieldName} has ${value.length} items (max recommended: ${arrayConfig.maxLength})`);
            }

            // Warn if empty (but still valid)
            if (arrayConfig.warnIfEmpty && value.length === 0) {
                result.warnings.push(`${fieldName} is empty - no data to display`);
            }

            // Validate array items if itemSchema provided
            if (itemSchema && value.length > 0) {
                const maxItemsToValidate = Math.min(value.length, 10); // Validate first 10 items for performance
                for (let i = 0; i < maxItemsToValidate; i++) {
                    if (itemSchema.fields) {
                        this._validateFields(value[i], itemSchema.fields, `${fieldName}[${i}]`, result);
                    }
                }
            }

            return result;
        },

        /**
         * Validate object fields
         * @param {Object} data - Data object to validate
         * @param {Object} fields - Field definitions
         * @param {string} prefix - Path prefix for error messages
         * @param {ValidationResult} result - Result object to update
         */
        _validateFields(data, fields, prefix, result) {
            if (typeof data !== 'object' || data === null) {
                result.valid = false;
                result.errors.push(`${prefix || 'Data'} must be an object`);
                return;
            }

            for (const [fieldName, fieldDef] of Object.entries(fields)) {
                const fullPath = prefix ? `${prefix}.${fieldName}` : fieldName;
                const value = data[fieldName];

                // Check required fields
                if (fieldDef.required && (value === undefined || value === null)) {
                    result.valid = false;
                    result.errors.push(`Missing required field: ${fullPath}`);
                    continue;
                }

                // Skip validation for undefined optional fields
                if (value === undefined || value === null) {
                    continue;
                }

                // Type validation
                const typeResult = this._validateType(value, fieldDef.type, fullPath);
                if (!typeResult.valid) {
                    result.valid = false;
                    result.errors.push(typeResult.error);
                    continue;
                }

                // Range validation for numbers
                if (fieldDef.type === 'number') {
                    this._validateRange(value, fieldDef, fullPath, result);
                }

                // Length validation for strings and arrays
                if (fieldDef.type === 'string' || fieldDef.type === 'array') {
                    this._validateLength(value, fieldDef, fullPath, result);
                }

                // Pattern validation for strings
                if (fieldDef.type === 'string' && fieldDef.pattern) {
                    if (!new RegExp(fieldDef.pattern).test(value)) {
                        result.warnings.push(`${fullPath} does not match expected pattern`);
                    }
                }

                // Nested object validation
                if (fieldDef.type === 'object' && fieldDef.properties) {
                    this._validateFields(value, fieldDef.properties, fullPath, result);
                }

                // Warn conditions
                if (fieldDef.warnIf) {
                    this._checkWarnCondition(value, fieldDef.warnIf, fullPath, result);
                }
            }
        },

        /**
         * Validate nested arrays in an object
         * @param {Object} data - Data object containing arrays
         * @param {Object} nestedArrays - Nested array configurations
         * @param {ValidationResult} result - Result object to update
         */
        _validateNestedArrays(data, nestedArrays, result) {
            for (const [path, config] of Object.entries(nestedArrays)) {
                const value = this._getNestedValue(data, path);
                if (Array.isArray(value) && config.itemSchema) {
                    const maxItemsToValidate = Math.min(value.length, 10);
                    for (let i = 0; i < maxItemsToValidate; i++) {
                        if (config.itemSchema.fields) {
                            this._validateFields(value[i], config.itemSchema.fields, `${path}[${i}]`, result);
                        }
                    }
                }
            }
        },

        /**
         * Validate value type
         * @param {*} value - Value to check
         * @param {string} expectedType - Expected type
         * @param {string} fieldPath - Field path for error messages
         * @returns {{valid: boolean, error?: string}}
         */
        _validateType(value, expectedType, fieldPath) {
            switch (expectedType) {
                case 'string':
                    if (typeof value !== 'string') {
                        return { valid: false, error: `${fieldPath} must be a string` };
                    }
                    break;
                case 'number':
                    if (typeof value !== 'number' || isNaN(value)) {
                        return { valid: false, error: `${fieldPath} must be a valid number` };
                    }
                    break;
                case 'boolean':
                    if (typeof value !== 'boolean') {
                        return { valid: false, error: `${fieldPath} must be a boolean` };
                    }
                    break;
                case 'array':
                    if (!Array.isArray(value)) {
                        return { valid: false, error: `${fieldPath} must be an array` };
                    }
                    break;
                case 'object':
                    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
                        return { valid: false, error: `${fieldPath} must be an object` };
                    }
                    break;
                case 'date':
                    // Accept strings that can be parsed as dates, or Date objects
                    if (value instanceof Date) {
                        if (isNaN(value.getTime())) {
                            return { valid: false, error: `${fieldPath} must be a valid date` };
                        }
                    } else if (typeof value === 'string') {
                        const parsed = new Date(value);
                        if (isNaN(parsed.getTime())) {
                            return { valid: false, error: `${fieldPath} must be a valid date string` };
                        }
                    } else {
                        return { valid: false, error: `${fieldPath} must be a date` };
                    }
                    break;
            }
            return { valid: true };
        },

        /**
         * Validate numeric range
         * @param {number} value - Numeric value
         * @param {FieldDefinition} fieldDef - Field definition with min/max
         * @param {string} fieldPath - Field path for error messages
         * @param {ValidationResult} result - Result object to update
         */
        _validateRange(value, fieldDef, fieldPath, result) {
            if (fieldDef.min !== undefined && value < fieldDef.min) {
                result.valid = false;
                result.errors.push(`${fieldPath} must be at least ${fieldDef.min}, got ${value}`);
            }
            if (fieldDef.max !== undefined && value > fieldDef.max) {
                result.warnings.push(`${fieldPath} value ${value} exceeds expected maximum ${fieldDef.max}`);
            }
        },

        /**
         * Validate string/array length
         * @param {string|Array} value - Value to check
         * @param {FieldDefinition} fieldDef - Field definition with minLength/maxLength
         * @param {string} fieldPath - Field path for error messages
         * @param {ValidationResult} result - Result object to update
         */
        _validateLength(value, fieldDef, fieldPath, result) {
            const length = value.length;
            if (fieldDef.minLength !== undefined && length < fieldDef.minLength) {
                result.valid = false;
                result.errors.push(`${fieldPath} must have at least ${fieldDef.minLength} items/characters, got ${length}`);
            }
            if (fieldDef.maxLength !== undefined && length > fieldDef.maxLength) {
                result.warnings.push(`${fieldPath} has ${length} items/characters (max recommended: ${fieldDef.maxLength})`);
            }
        },

        /**
         * Check warning condition
         * @param {*} value - Value to check
         * @param {string} condition - Warning condition: 'empty', 'low', 'high'
         * @param {string} fieldPath - Field path for warning messages
         * @param {ValidationResult} result - Result object to update
         */
        _checkWarnCondition(value, condition, fieldPath, result) {
            switch (condition) {
                case 'empty':
                    if (Array.isArray(value) && value.length === 0) {
                        result.warnings.push(`${fieldPath} is empty - no data to display`);
                    } else if (typeof value === 'object' && Object.keys(value).length === 0) {
                        result.warnings.push(`${fieldPath} is empty - no data to display`);
                    }
                    break;
                case 'low':
                    if (typeof value === 'number' && value === 0) {
                        result.warnings.push(`${fieldPath} is zero`);
                    }
                    break;
                case 'high':
                    // Can be used for specific thresholds in custom schemas
                    break;
            }
        },

        /**
         * Get nested value from object by path
         * @param {Object} obj - Object to traverse
         * @param {string} path - Dot-separated path
         * @returns {*} Value at path or undefined
         */
        _getNestedValue(obj, path) {
            return path.split('.').reduce((current, key) => {
                return current && current[key] !== undefined ? current[key] : undefined;
            }, obj);
        },

        /**
         * Convenience method to validate and check if data is renderable
         * @param {*} data - Data to validate
         * @param {ValidationSchema} schema - Schema to validate against
         * @param {Object} options - Options for validation behavior
         * @param {boolean} [options.allowEmpty=true] - Allow empty arrays/objects (shows warning)
         * @returns {ValidationResult}
         */
        validate(data, schema, options = {}) {
            const { allowEmpty = true } = options;
            const result = this.validateForView(data, schema);

            // If not allowing empty, convert empty warnings to errors
            if (!allowEmpty && result.warnings.some(w => w.includes('is empty'))) {
                result.valid = false;
                result.errors.push(...result.warnings.filter(w => w.includes('is empty')));
                result.warnings = result.warnings.filter(w => !w.includes('is empty'));
            }

            return result;
        },

        /**
         * Create a custom schema
         * @param {string} name - Schema name
         * @param {Object} fields - Field definitions
         * @param {Object} [options] - Additional options
         * @returns {ValidationSchema}
         */
        createSchema(name, fields, options = {}) {
            return {
                name,
                fields,
                ...options
            };
        },

        /**
         * Display validation warnings inline in a container
         * @param {HTMLElement|string} container - Container element or selector
         * @param {string[]} warnings - Array of warning messages
         * @param {Object} [options] - Display options
         */
        showWarnings(container, warnings, options = {}) {
            if (!warnings || warnings.length === 0) return;

            const containerEl = typeof container === 'string'
                ? document.querySelector(container)
                : container;

            if (!containerEl) {
                log.warn('Container not found for warnings:', container);
                return;
            }

            const { position = 'prepend', className = '' } = options;

            // Create warning element
            const warningEl = document.createElement('div');
            warningEl.className = `data-validation-warning ${className}`;
            warningEl.setAttribute('role', 'alert');
            warningEl.innerHTML = `
                <span class="data-validation-warning__icon" aria-hidden="true">⚠️</span>
                <span class="data-validation-warning__text">
                    ${this._escapeHtml(warnings.length === 1 ? warnings[0] : `${warnings.length} data quality issues detected`)}
                </span>
                ${warnings.length > 1 ? `
                    <button class="data-validation-warning__toggle" aria-expanded="false">
                        Show details
                    </button>
                    <ul class="data-validation-warning__list hidden">
                        ${warnings.map(w => `<li>${this._escapeHtml(w)}</li>`).join('')}
                    </ul>
                ` : ''}
            `;

            // Add toggle functionality
            const toggleBtn = warningEl.querySelector('.data-validation-warning__toggle');
            if (toggleBtn) {
                toggleBtn.addEventListener('click', function() {
                    const list = warningEl.querySelector('.data-validation-warning__list');
                    const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';
                    toggleBtn.setAttribute('aria-expanded', !isExpanded);
                    toggleBtn.textContent = isExpanded ? 'Show details' : 'Hide details';
                    list.classList.toggle('hidden', isExpanded);
                });
            }

            // Insert warning
            if (position === 'prepend') {
                containerEl.insertBefore(warningEl, containerEl.firstChild);
            } else {
                containerEl.appendChild(warningEl);
            }

            log.debug('Validation warnings displayed', { count: warnings.length });
        },

        /**
         * Clear validation warnings from container
         * @param {HTMLElement|string} container - Container element or selector
         */
        clearWarnings(container) {
            const containerEl = typeof container === 'string'
                ? document.querySelector(container)
                : container;

            if (!containerEl) return;

            const warnings = containerEl.querySelectorAll('.data-validation-warning');
            warnings.forEach(el => el.remove());
        },

        /**
         * Escape HTML to prevent XSS
         * @private
         */
        _escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    };

    // Expose to global scope
    global.DataValidator = DataValidator;
    global.DATA_VALIDATION_SCHEMAS = SCHEMAS;

    // Also expose individual validators for direct use
    global.validateArray = function(arr, options = {}) {
        const config = {
            minLength: options.minLength || 0,
            maxLength: options.maxLength,
            warnIfEmpty: options.warnIfEmpty !== false
        };
        const result = { valid: true, errors: [], warnings: [], metadata: {} };
        return DataValidator._validateArray(arr, config, options.itemSchema, options.name || 'Array', result);
    };

    global.validateFields = function(data, fields, options = {}) {
        const result = { valid: true, errors: [], warnings: [], metadata: {} };
        DataValidator._validateFields(data, fields, options.prefix || '', result);
        return result;
    };

    global.validateType = function(value, type, fieldName = 'value') {
        return DataValidator._validateType(value, type, fieldName);
    };

    global.validateRange = function(value, min, max, fieldName = 'value') {
        const result = { valid: true, errors: [], warnings: [], metadata: {} };
        DataValidator._validateRange(value, { min, max }, fieldName, result);
        return result;
    };

})(typeof window !== 'undefined' ? window : this);
