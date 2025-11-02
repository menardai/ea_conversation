# PRD — LLM→TTS WebSocket Service

## 1. Overview
This project delivers a **WebSocket-based backend service** that accepts text from a client, sends it to an OpenAI LLM for response generation, and synthesizes the reply into audio using OpenAI TTS.  
The resulting audio is then sent back to the client through the same WebSocket connection.  

The MVP focuses on generating and returning the **complete audio file** once TTS synthesis completes.  
A **Phase 2** iteration will extend the system to **stream audio chunks** as they are produced.

---

## 2. Goals & Success Criteria

### Goals
- Provide a simple, low-latency **text→speech WebSocket pipeline**.
- Demonstrate clean **asynchronous architecture** with modular components.
- Ensure the system is **easy to deploy, configure, and test**.
- Lay the foundation for future streaming and scaling.

### Success Criteria
- The server can handle multiple concurrent WebSocket clients.
- Each client can send text and receive an audio file (binary) response.
- Average end-to-end response latency < **5 seconds** for short text (< 50 words).
- The service is configurable via environment variables.
- A simple Python test client can connect, send text, and play or save the received audio.

---

## 3. Technical Stack

| Layer | Choice | Rationale |
|-------|---------|------------|
| Framework | **FastAPI** | Modern async Python web framework with WS + HTTP routes, Pydantic validation, and built-in docs. |
| Server | **Uvicorn (ASGI)** | Lightweight, high-performance async server compatible with FastAPI. |
| HTTP Client | **httpx.AsyncClient** | Reliable async HTTP client to call OpenAI APIs. |
| Model | **gpt-4o-mini** | Fast, cost-effective LLM for short conversational text generation. |
| TTS Engine | **OpenAI TTS (tts-1, voice = alloy)** | High-quality neural voice synthesis with fast generation. |
| Language | **Python 3.11+** | Stable async support and mature ecosystem. |

---

## 4. Functional Requirements

### 4.1 WebSocket Behavior
- **Endpoint:** `/ws`
- **Input message (JSON):**  
  ```json
  { "text": "Your input text here" }
  ```
- **Output message (binary):**  
  - Audio data (MIME type: `audio/mpeg` or `audio/opus`)  
  - Metadata (optional JSON header for debugging)

### 4.2 API Flow
1. Client connects via WebSocket.
2. Client sends JSON payload containing `text`.
3. Server sends text to **OpenAI Chat Completions** API.
4. Server receives LLM text reply.
5. Server sends reply text to **OpenAI TTS API**.
6. TTS response is converted into a complete audio file.
7. Audio file is sent back to client as a single binary WebSocket frame.
8. Connection stays open for subsequent messages or closes gracefully.

### 4.3 HTTP Endpoints
- `/healthz`: health check returning `"ok"`.
- `/version`: returns app version and environment.
- Optional `/metrics`: for observability (Phase 2).

### 4.4 Configuration
All configurable parameters will be set via environment variables (using `pydantic-settings`):

| Variable | Default | Description |
|-----------|----------|-------------|
| `OPENAI_API_KEY` | — | OpenAI key with Chat + TTS access |
| `CHAT_MODEL` | `gpt-4o-mini` | Model used for LLM responses |
| `TTS_MODEL` | `tts-1` | Voice synthesis model |
| `TTS_VOICE` | `alloy` | Default voice |
| `LOG_LEVEL` | `info` | Logging verbosity |
| `PORT` | `8000` | Server port |
| `MAX_TEXT_LENGTH` | `1000` | Input limit per message |

---

## 5. Non-Functional Requirements (NFRs)

| Category | Requirement |
|-----------|--------------|
| **Performance** | P50 latency < 5s, P95 < 8s for short inputs |
| **Concurrency** | ≥ 50 active clients per worker |
| **Security** | All traffic served over TLS; keys read from env only |
| **Reliability** | Graceful reconnects; no data corruption on disconnect |
| **Scalability** | Horizontally scalable via multiple ASGI workers |
| **Observability** | Structured logs (JSON); minimal metrics |
| **Configurability** | Environment variables for all tunables |

---

## 6. Deliverables

### 6.1 Source Code
- `app/main.py` — FastAPI entrypoint  
- `app/websocket_handlers.py` — WS endpoints  
- `app/services/chat_service.py` — OpenAI chat logic  
- `app/services/tts_service.py` — OpenAI TTS logic  
- `app/config.py` — environment & settings  
- `tests/` — basic test coverage  

### 6.2 Test Client
- `client/test_client.py` — simple async WS client to:
  - Connect to server  
  - Send sample text  
  - Receive binary audio and save as `output.mp3`

### 6.3 Documentation
- **README.md** with:
  - Installation & dependencies  
  - `.env` configuration sample  
  - Run command (`uvicorn app.main:app --reload`)  
  - How to test with included client  
  - Troubleshooting section

---

## 7. Error Handling
- Reject messages > `MAX_TEXT_LENGTH` with JSON error frame.
- Catch OpenAI API exceptions → return error message to client.
- Handle dropped WS connections gracefully.
- Log all errors with request context and timestamps.

---

## 8. Future Enhancements (Phase 2)
- **Audio streaming mode:** send TTS audio in chunks as they are generated.
- **Authentication:** optional API key or JWT for clients.
- **Rate limiting:** per-connection and per-IP request caps.
- **Metrics & monitoring:** Prometheus / OpenTelemetry integration.
- **Voice selection:** allow client to choose voice per message.
- **Persistent logs & tracing:** for debugging long-running sessions.

---

## 9. Risks & Mitigation

| Risk | Impact | Mitigation |
|-------|---------|------------|
| Long synthesis delays | Medium | Set timeout for LLM/TTS calls; return friendly error |
| Client disconnects mid-TTS | Low | Cancel pending tasks, cleanup buffers |
| Misconfigured env vars | Medium | Pydantic validation with clear startup logs |
| OpenAI API quota exceeded | Medium | Retry with exponential backoff; alert |
| High concurrency causing lag | Medium | Limit concurrent tasks per connection |

---

## 10. Milestones

| Milestone | Deliverable | ETA |
|------------|--------------|-----|
| **MVP v1.0** | Full-file audio return over WebSocket | Week 1 |
| **v1.1** | Add streaming audio chunks | Week 2–3 |
| **v1.2** | Add metrics, rate limits, improved test client | Week 4 |

---

## 11. Summary
This PRD defines a modular, async WebSocket service using **FastAPI + Uvicorn**, capable of generating speech from LLM responses via OpenAI APIs.  
The MVP prioritizes reliability and simplicity, while the architecture cleanly supports later improvements such as **real-time audio streaming**, **observability**, and **authentication**.

