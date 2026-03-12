/**
 * ChatEngine — Shared chat protocol and logic engine.
 *
 * Framework-agnostic. Handles:
 *   - Conversation history management
 *   - SSE streaming from Lambda backend
 *   - Context collection (caller-provided)
 *   - localStorage persistence
 *
 * Each project wraps this in its own UI layer:
 *   - coefficientgiving: vanilla JS IIFE (chatbot.js)
 *   - family-org: React <ChatPanel> component
 *
 * @module ChatEngine
 */
const ChatEngine = (() => {
    'use strict';

    const DEFAULTS = {
        maxHistory: 10,
        storageKey: 'chat-engine-history',
    };

    /**
     * Create a new chat engine instance.
     *
     * @param {Object} config
     * @param {string} config.apiEndpoint — Base URL of the chat API
     * @param {Function} [config.collectContext] — Returns page context object
     * @param {Function} [config.onChunk] — Called with each streamed text chunk
     * @param {Function} [config.onComplete] — Called when response is complete: { text, sources }
     * @param {Function} [config.onError] — Called on error
     * @param {number} [config.maxHistory=10] — Max messages to keep
     * @param {string} [config.storageKey] — localStorage key for persistence
     * @returns {Object} Engine instance
     */
    function create(config) {
        const cfg = Object.assign({}, DEFAULTS, config);
        let history = [];
        let isStreaming = false;
        let abortController = null;

        // Load persisted history
        _loadHistory();

        /**
         * Send a message and stream the response.
         * @param {string} message — User's message text
         * @returns {Promise<{text: string, sources: Array}>}
         */
        async function send(message) {
            if (isStreaming) throw new Error('Already streaming');
            if (!message.trim()) throw new Error('Empty message');

            isStreaming = true;
            abortController = new AbortController();

            // Add user message to history
            history.push({ role: 'user', content: message });

            const context = cfg.collectContext ? cfg.collectContext() : {};

            try {
                const resp = await fetch(cfg.apiEndpoint + '/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    signal: abortController.signal,
                    body: JSON.stringify({
                        message: message,
                        conversation_history: history.slice(-(cfg.maxHistory)),
                        page_context: context,
                        stream: true,
                    }),
                });

                if (!resp.ok) {
                    throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
                }

                const contentType = resp.headers.get('content-type') || '';

                let fullText = '';
                let sources = [];

                if (contentType.includes('text/event-stream')) {
                    // SSE streaming response
                    const reader = resp.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        buffer += decoder.decode(value, { stream: true });

                        // Process complete SSE events
                        const lines = buffer.split('\n');
                        buffer = lines.pop(); // keep incomplete line

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                const data = line.slice(6);
                                if (data === '[DONE]') continue;

                                try {
                                    const evt = JSON.parse(data);
                                    if (evt.type === 'chunk' && evt.text) {
                                        fullText += evt.text;
                                        if (cfg.onChunk) cfg.onChunk(evt.text);
                                    } else if (evt.type === 'sources') {
                                        sources = evt.sources || [];
                                    } else if (evt.type === 'error') {
                                        throw new Error(evt.message || 'Stream error');
                                    }
                                } catch (parseErr) {
                                    // Skip unparseable lines
                                }
                            }
                        }
                    }
                } else {
                    // Non-streaming JSON fallback
                    const data = await resp.json();
                    fullText = data.response || '';
                    sources = data.sources || [];
                    if (cfg.onChunk) cfg.onChunk(fullText);
                }

                // Add assistant response to history
                history.push({ role: 'assistant', content: fullText });
                _trimHistory();
                _saveHistory();

                const result = { text: fullText, sources: sources };
                if (cfg.onComplete) cfg.onComplete(result);

                return result;

            } catch (err) {
                if (err.name === 'AbortError') {
                    // User cancelled — don't report as error
                    return { text: '', sources: [] };
                }
                if (cfg.onError) cfg.onError(err);
                throw err;
            } finally {
                isStreaming = false;
                abortController = null;
            }
        }

        /** Cancel an in-progress stream. */
        function cancel() {
            if (abortController) abortController.abort();
        }

        /** Get conversation history. */
        function getHistory() {
            return [...history];
        }

        /** Clear conversation history. */
        function clearHistory() {
            history = [];
            _saveHistory();
        }

        /** @returns {boolean} Whether a response is currently streaming. */
        function streaming() {
            return isStreaming;
        }

        // ---- internal ----

        function _trimHistory() {
            if (history.length > cfg.maxHistory * 2) {
                history = history.slice(-cfg.maxHistory * 2);
            }
        }

        function _saveHistory() {
            try {
                const key = cfg.storageKey;
                localStorage.setItem(key, JSON.stringify(history.slice(-cfg.maxHistory)));
            } catch (e) { /* storage unavailable */ }
        }

        function _loadHistory() {
            try {
                const saved = localStorage.getItem(cfg.storageKey);
                if (saved) history = JSON.parse(saved);
            } catch (e) { /* storage unavailable */ }
        }

        return { send, cancel, getHistory, clearHistory, streaming };
    }

    return { create };
})();

// Support both browser globals and CommonJS/ESM
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChatEngine;
}
