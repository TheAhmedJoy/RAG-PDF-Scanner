# RAG PDF Scanner

A local Retrieval-Augmented Generation (RAG) app for PDFs. Drop a PDF into the UI, the backend chunks and embeds it into a Qdrant vector store, and you can then ask natural-language questions about the document — answered by an OpenAI model grounded in the chunks that were actually retrieved.

The project is wired together with **FastAPI** (HTTP API), **Inngest** (durable, observable workflows), **LlamaIndex** (PDF parsing + chunking), **Qdrant** (vector database, running locally in Docker), **OpenAI** (embeddings + LLM), and a **Streamlit** UI.

---

## What the product does

The app has two flows, both triggered as Inngest events from the Streamlit UI.

**Ingest a PDF**
1. The user uploads a PDF in the Streamlit UI; it's saved to `uploads/`.
2. Streamlit fires the `rag/ingest_pdf` Inngest event with the file path.
3. The Inngest function `rag_inngest_pdf` runs two durable steps:
   - `load-and-chunk-pdf` — `PDFReader` from `llama-index-readers-file` reads the PDF, then `SentenceSplitter` (chunk size 1000, overlap 200) breaks it into chunks.
   - `embed-and-upsert` — calls OpenAI `text-embedding-3-large` (3072-dim) and upserts the vectors into a Qdrant collection called `docs` with `(source, text)` payloads. Point IDs are deterministic UUID5s so re-ingesting the same source replaces existing points.

**Ask a question**
1. The user types a question in the Streamlit UI and picks `top_k`.
2. Streamlit fires the `rag/query_pdf_ai` Inngest event and polls Inngest's local dev API for the run's output.
3. The Inngest function `rag_query_pdf_ai` runs:
   - `embed-and-search` — embeds the question and queries Qdrant for the `top_k` most similar chunks, returning their texts and sources.
   - `llm-answer` — assembles a prompt with the retrieved context and asks an OpenAI chat model to answer concisely using only that context (via Inngest's `ai.openai.Adapter`).
4. The answer and the deduplicated source list are rendered back in Streamlit.

Pydantic models (`RAGChunkAndSrc`, `RAGUpsertResult`, `RAGSearchResult`) are used for typed step inputs/outputs so Inngest can serialise the workflow state.

---

## Tech stack

**Language & runtime**
- Python ≥ 3.14
- [`uv`](https://docs.astral.sh/uv/) for project + dependency management

**Backend**
- **FastAPI** — host for the Inngest webhook (`/api/inngest`)
- **Inngest** (`inngest` Python SDK) — durable workflow engine; functions are exposed via `inngest.fast_api.serve(...)`
- **Uvicorn** — ASGI server

**RAG pipeline**
- **LlamaIndex** (`llama-index-core`, `llama-index-readers-file`) — PDF reading + sentence splitting
- **OpenAI** — `text-embedding-3-large` for embeddings and a GPT chat model for answer synthesis (configured inside `main.py`)
- **Qdrant** — vector database, run locally in Docker; accessed via `qdrant-client`

**Frontend**
- **Streamlit** — single-page UI with upload widget and Q&A form

**Configuration**
- `python-dotenv` — loads `OPENAI_API_KEY` (and optionally `INNGEST_API_BASE`) from a local `.env`

---

## Project structure

```
RAG-PDF-Scanner/
├── main.py              # FastAPI app + Inngest functions (ingest + query)
├── streamlit_app.py     # Streamlit UI (upload, ask)
├── data_loader.py       # PDF read, chunk, OpenAI embeddings
├── vector_db.py         # QdrantStorage wrapper (collection, upsert, search)
├── custom_types.py      # Pydantic models for Inngest step I/O
├── pyproject.toml       # uv project + dependencies
├── uv.lock
└── README.md
```
---

## Deployment (AWS EC2)

The app has also been deployed to a single AWS EC2 instance for live testing.

- **Instance:** `t2.micro` running **Ubuntu 22.04**
- **Process management:** All four services — FastAPI (Uvicorn), the Inngest dev server, the Qdrant container, and the Streamlit UI — are run together via a **`docker-compose.yml`** file, so a single `docker compose up -d` brings the whole stack online and `docker compose down` tears it down
- **Networking:** The Streamlit port is opened directly through the EC2 **security group**, so users hit Streamlit from the public IP without a reverse proxy in front of it (no Nginx, no domain, no HTTPS termination, aimed for ease of use)
- **Persistence:** The Qdrant volume is mounted from the host so ingested vectors survive container restarts
- **Status:** Hosting is intermittent because a `t2.micro` isn't free forever and the app gets very little traffic, the instance may be stopped at any time. When it's running, the URL is shared in the repo description. You can view the live demo at `http://18.119.126.28:8501/`
- **Live Inngest dashboard:** The Inngest dev server's UI (port `8288`) is also exposed through the security group, so you can watch events fire and step-by-step function runs in real time at `http://18.119.126.28:8288` while the app is up.
- **Want to run it yourself?** Instructions for setting it up locally are below.

---

## Prerequisites

- **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** installed and running. Qdrant runs as a local Docker container, so Docker Desktop is required before you start anything.
- **Python 3.14+** (uv will install it for you if needed)
- **Node.js / npx** (used to run the local Inngest dev server)
- An **OpenAI API key**

Create a `.env` file in the project root:

- **You must provide your own OpenAI API Key in the .env**

```env
OPENAI_API_KEY=sk-...
```

---

## Getting started

You'll end up with **four terminals open**, one for each long-running process. Run the steps in order.

### 1. Initialize the project and install dependencies

```bash
uv init .

uv add fastapi inngest llama-index-core llama-index-readers-file python-dotenv qdrant-client uvicorn streamlit openai
```

### 2. Start the FastAPI / Inngest backend

```bash
uv run uvicorn main:app
```

This serves the Inngest functions at `http://127.0.0.1:8000/api/inngest`.

### 3. In a **new terminal**, start the local Inngest dev server

```bash
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery
```

This launches the Inngest dashboard (typically at `http://127.0.0.1:8288`) and registers the FastAPI app's functions so events can be dispatched and runs can be observed.

### 4. In a **new terminal**, start Qdrant in Docker

```bash
docker run -d --name qdrantRagDb -p 6333:6333 -v "$(pwd)/qrdant_storage:/qdrant/storage" qdrant/qdrant
```

This creates and starts a container called `qdrantRagDb`, exposes port `6333`, and persists data to `./qrdant_storage` on your host so vectors survive restarts. After the first run, subsequent sessions only need `docker start qdrantRagDb`.

### 5. In a **new terminal**, start the Streamlit UI

```bash
uv run streamlit run .\streamlit_app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`), upload a PDF to ingest it, and then ask questions in the form below.

---

## How it fits together

```
Streamlit UI  ──fires events──►  Inngest Dev Server  ──dispatches──►  FastAPI / Inngest functions
                                                                              │
                                                              ┌───────────────┼─────────────────┐
                                                              ▼               ▼                 ▼
                                                       OpenAI Embeddings  Qdrant (Docker)  OpenAI Chat
```

- Streamlit never calls OpenAI or Qdrant directly — it only sends Inngest events and polls Inngest for the resulting run output.
- The FastAPI process is what actually executes the Inngest functions; the Inngest dev server is the orchestrator/observer.
- Qdrant lives in its own Docker container at `localhost:6333`.

---
