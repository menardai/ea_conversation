# FastAPI + Uvicorn for an LLM→TTS WebSocket Service
**Decision note — pros & cons, with risks and mitigations**

## Summary
FastAPI (on Starlette/ASGI) with Uvicorn is a strong fit for a WebSocket service that accepts text, calls OpenAI Chat Completions, converts the response with TTS, and returns audio to the client. It balances **developer experience, performance, and extensibility** without imposing heavy infrastructure. The trade-offs mostly concern **async discipline**, **WebSocket scaling specifics**, and **building some middleware (auth/rate-limits)** yourself.

---

## Strengths (Pros)

### 1) Modern async stack, good performance
- **ASGI-native**: FastAPI+Starlette is built for `asyncio`, which maps well to IO-bound workloads (OpenAI HTTP calls, file IO, WebSocket frames).  
- **Low overhead**: Uvicorn (with optional `uvloop`) provides fast event-loop performance suitable for many concurrent WS connections.  
- **Great for streaming later**: The stack makes it straightforward to evolve from “send whole file” to **chunked audio streaming**.

### 2) Clean structure and modularity
- **Unified app** for WebSocket and HTTP routes: e.g., `/ws` plus `/healthz`, `/ready`, `/version`.  
- **Pydantic models** for message validation, environment-based settings, and configuration sanity.  
- **Layered design**: easy to separate `adapters` (OpenAI clients), `services` (LLM+TTS orchestration), and `transport` (WS).

### 3) Developer experience & ecosystem
- **Fast to iterate**: type hints, auto-reload in dev, helpful errors.  
- **Testing**: nice support for HTTP routes via TestClient, and plenty of examples for WS testing with `pytest-asyncio`.  
- **Documentation**: automatic OpenAPI for HTTP endpoints aids ops (health checks), even if WS doesn’t expose OpenAPI.

### 4) Observability & operations
- **Middlewares** for request IDs, structured logging, and CORS are easy to add.  
- Prometheus metrics / OpenTelemetry can be integrated with standard ASGI middlewares.  
- Health and readiness endpoints are standard patterns for container orchestration.

### 5) Deployment flexibility
- **ASGI-first**: runs on Uvicorn/Hypercorn; easy containerization.  
- **Horizontal scaling** with multiple workers/processes is straightforward; compatible with common ingress controllers and reverse proxies.

### 6) Good long-term extensibility
- If you later add **auth**, web dashboards, or admin HTTP endpoints, the framework already supports them.  
- Swap dependencies easily (e.g., `httpx` vs official SDKs), plug in queues, or add background tasks for post-processing.

---

## Limitations (Cons)

### 1) Async discipline is required
- Blocking calls (e.g., CPU-heavy audio transforms) will **block the event loop**; you must isolate them (process/thread pools) or avoid them.  
- Misuse of sync libraries inside handlers can cause **latency spikes** for all clients.

**Mitigation**:  
- Enforce async-only IO (e.g., `httpx.AsyncClient` for OpenAI).  
- Offload rare CPU-bound work to `asyncio.to_thread` or a worker process (but keep MVP simple).

### 2) WebSocket scaling nuances
- WebSockets require **long-lived connections** and sticky routing (or at least consistent session handling) behind load balancers.  
- Some managed platforms have **idle timeouts** or strict WS limits.

**Mitigation**:  
- Validate load balancer WS support (keepalives, idle timeouts).  
- Consider **per-connection limits**: max message size, max concurrent connections per IP, and sensible server timeouts.  
- Add keepalive pings.

### 3) You build some platform features yourself
- No built-in **rate limiting**, **quotas**, or **auth** for WS.  
- You’ll need to add **input validation** and **backpressure handling** (e.g., rejecting oversized messages).

**Mitigation**:  
- Lightweight middlewares or dependency injection to check bearer tokens / API keys.  
- Simple in-memory rate limiter (token bucket) for MVP; external cache later (Redis) if needed.

### 4) WebSocket testing is a bit more manual than HTTP
- Fewer batteries than HTTP tests; you’ll likely write an **async test client** for realistic coverage.

**Mitigation**:  
- Provide a minimal Python WS client in `examples/` for manual and automated tests.  
- Use `pytest-asyncio` with a local server instance.

### 5) Not the absolute lowest overhead possible
- A raw `websockets` implementation can be **marginally faster** and lighter for WS-only, but loses FastAPI’s productivity features.

**Mitigation**:  
- Accept the tiny overhead for better **DX, validation, and future-proofing**.

---

## Fit for this project’s requirements

**Modularity & Structure**  
- Controllers: WS endpoint + small HTTP endpoints.  
- Services: `ChatService`, `TtsService`, `SynthesisOrchestrator`.  
- Adapters: OpenAI clients (chat/tts) via `httpx.AsyncClient`.  
- Config: `pydantic-settings` to declare models, voice, sampling rate, timeouts, etc.

**Concurrency Model**  
- Pure `asyncio`; one task per connection/message.  
- Optional **per-connection** semaphore to avoid user-induced flooding (e.g., 1 in-flight synthesis per connection).  
- Timeouts and cancellation tokens to release resources when clients disconnect.

**Error Handling & Robustness**  
- Central exception handlers for HTTP, and try/except blocks in WS loops.  
- Validate input (length, allowed characters), return **typed error frames** on failure.  
- Retries with **circuit breakers** for transient OpenAI errors (e.g., `tenacity`), with conservative budgets.

**Dependency Choices**  
- **FastAPI**, **Uvicorn** (core).  
- **httpx** (async HTTP) for OpenAI calls; use the official SDK if it cleanly supports asyncio and streaming.  
- **pydantic** / **pydantic-settings** for config and request models.  
- **tenacity** for retries with jitter and backoff.  
- Optional: **uvloop** in prod for performance.

**Verification & Testing**  
- Unit tests for services (mock OpenAI).  
- Integration test: start the server in-process and verify WS request → LLM → TTS → audio bytes returned.  
- Smoke tests for health endpoints.  
- Load “sanity” testing: N concurrent clients with short inputs to validate backpressure/limits.

**Documentation & Usability**  
- README: quickstart, `.env` config, how to run, how to test (CLI client example).  
- Troubleshooting section (timeouts, permissions, audio devices on client).

---

## Security & Compliance considerations

- **Secret management**: OpenAI API key via environment variables; never log it.  
- **Least privilege**: minimal scopes; consider per-project keys.  
- **Input sanitization**: check payload sizes; guard against injection into logs.  
- **Rate limits & quotas** to control cost and abuse.  
- **CORS** (for any HTTP routes) and **origin checks** for WS in browser scenarios.  
- **TLS**: terminate at the load balancer or run Uvicorn behind a TLS terminator.  
- **PII**: avoid storing input/output unless explicitly needed; document retention.

---

## Performance notes

- **MVP path (non-streaming audio)** keeps server logic simple:  
  1) receive text → 2) call chat → 3) call TTS → 4) return a **single binary frame** (e.g., `audio/mpeg` or `audio/opus`).  
- For streaming later: chunked frames via WS; ensure the client can **play as it receives** and handle out-of-order/late chunks.  
- Set **timeouts** for LLM and TTS calls; short circuit on client disconnects.  
- Use **bounded concurrency** and **connection limits** to protect upstream and budget.

---

## Deployment & scaling

- **Containerized** app running Uvicorn; 1–4 workers initially.  
- Horizontal scale behind a reverse proxy that supports WebSockets.  
- **Sticky sessions** not strictly required if each connection is self-contained (no shared memory), but be mindful of **per-pod connection capacity**.  
- Autoscale on CPU and **concurrent connections** or request latency; keep per-worker memory in check (audio buffers).

---

## Alternatives briefly (for context)

- **`websockets` library only**: fastest to bare metal WS; fewer features, more custom code for health/auth/metrics.  
- **`aiohttp`**: solid WS+HTTP, but fewer DX niceties than FastAPI (validation/docs).  
- **Node.js (ws/Fastify)**: good for WS streaming, but mismatched with the “Python” ask and Pydantic benefits.

---

## Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Long TTS/LLM latency leads to timeouts | Failed user requests | Timeouts + retries + surface “busy/try again”; cap input length |
| Memory pressure from large audio buffers | Pod OOM/restarts | Enforce max input length, max audio duration; stream in future |
| Event loop blocked by sync code | Global stalls | Audit dependencies; offload CPU-bound work; linters for async |
| Cost spikes (abuse or bugs) | Budget overrun | Per-connection and per-IP rate limits; logging & daily usage alerts |
| Load balancer WS quirks/timeouts | Disconnections | Keepalives; validate platform WS support; document client reconnect |

---

## Bottom line
**FastAPI + Uvicorn** is an excellent choice for this LLM→TTS WebSocket MVP: **clean structure**, **async performance**, and **future-proofing** with modest complexity. The few drawbacks are well-understood and manageable with standard patterns (timeouts, limits, observability, and disciplined async usage).

