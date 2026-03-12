# Chat Engine

Shared chat widget engine for Coefficient Giving projects. Provides the core
protocol and logic for an embedded AI chat interface powered by Claude.

## Architecture

- **`chat-engine.js`** — Framework-agnostic chat engine (vanilla JS). Handles
  conversation history, SSE streaming, context collection, localStorage persistence.
- **Lambda backend** — Python Lambda with RAG over site content + Claude streaming.

## Usage (Vanilla JS)

```js
const engine = ChatEngine.create({
  apiEndpoint: 'https://your-api.execute-api.us-east-1.amazonaws.com',
  collectContext: () => ({ page: 'gear', filters: { owner: 'Wolf' } }),
  onChunk: (text) => appendToUI(text),
  onComplete: ({ text, sources }) => finalizeMessage(text, sources),
  onError: (err) => showError(err.message),
  maxHistory: 10,
  storageKey: 'my-chat-history',
});

await engine.send('What alignment approach handles this?');
engine.getHistory();  // [{role, content}, ...]
engine.clearHistory();
```

## Usage (React)

```tsx
import { useChatEngine } from './use-chat-engine';

function ChatPanel() {
  const { messages, send, isStreaming } = useChatEngine({
    apiEndpoint: '/api/chat',
    collectContext: () => ({ page: router.pathname }),
  });
  // render your own UI
}
```
