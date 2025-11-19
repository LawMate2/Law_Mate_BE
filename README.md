# DDD RAG Chatbot Server

FastAPI-based retrieval-augmented generation (RAG) service implemented with a Domain-Driven Design (DDD) layered architecture for managing documents, chat sessions, and observability around LLM-assisted conversations.

## Key Capabilities

- Clean separation of presentation, application, domain, and infrastructure layers.
- Document ingestion pipeline using LangChain loaders and chunking, FAISS vector storage, and OpenAI embeddings.
- Retrieval-augmented chat interactions backed by OpenAI ChatGPT and persistent session history.
- Google OAuth login flow with SQLAlchemy persistence for user profiles.
- MLflow tracking of document processing and chat metrics for experiment management.
- Korean Parliamentary Law portal integration that surfaces related legislation for each chat query.

## Tech Stack

- FastAPI, Pydantic, and Uvicorn
- SQLAlchemy ORM with MySQL (Docker) backend
- LangChain, FAISS, and OpenAI APIs
- MLflow for experiment tracking
- httpx for Google OAuth user infoY
- Python 3.11

## Architecture at a Glance

```text
[Client]
   |
[Presentation]  FastAPI routers (chat, documents, auth)
   |
[Application]   Use cases orchestrating services and repositories
   |
[Domain]        Entities, value objects, repository contracts
   |
[Infrastructure]SQLAlchemy + FAISS implementations, OpenAI, MLflow adapters
   |
[External]      MySQL, FAISS index on disk, OpenAI API, Google OAuth, MLflow
```

## Repository Layout

```text
.
├── main.py
├── app/
│   ├── presentation/
│   │   ├── controllers/      # FastAPI routers
│   │   └── schemas/          # Request/response DTOs
│   ├── application/          # Use cases and services (LLM, document processor)
│   ├── domain/               # Entities, value objects, repository interfaces
│   ├── infrastructure/       # SQLAlchemy + FAISS implementations
│   └── db/                   # SQLAlchemy models and session helpers
├── data/                     # FAISS index, uploads, MLflow runs
├── docker/                   # Docker Compose and MySQL assets
├── docker-data/              # Persisted MySQL volume (gitignored)
├── requirements.txt
└── test_main.http            # HTTPie/VSCode request samples
```

## Prerequisites

- Python 3.11 and `pip`
- Docker 20+ with Docker Compose v2
- An OpenAI API key with access to `gpt-3.5-turbo` and `text-embedding-ada-002`
- Optional: MLflow CLI for inspecting runs (`pip install mlflow`)

## Environment Configuration

Create a `.env` file at the repository root with the variables below (defaults come from `app/core/config.py`):

| Key | Default | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | (required) | OpenAI API key used for embeddings and chat completions |
| `FAISS_DB_PATH` | `./data/faiss` | Directory where the FAISS index and metadata are persisted |
| `UPLOAD_DIR` | `./data/uploads` | Directory for storing original uploaded documents |
| `MLFLOW_TRACKING_URI` | `./data/mlruns` | Path or URI for MLflow tracking storage |
| `MLFLOW_EXPERIMENT_NAME` | `rag-chatbot` | MLflow experiment name created on startup |
| `DB_DRIVER` | `mysql+pymysql` | SQLAlchemy database driver string |
| `DB_HOST` | `127.0.0.1` | MySQL host (matches the Docker Compose service) |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USERNAME` | `appuser` | Database username |
| `DB_PASSWORD` | `apppw` | Database password |
| `DB_DATABASE` | `appdb` | Database name |
| `ASSEMBLY_API_KEY` | (optional) | 의회·법률정보 포털 Open API 키 |
| `ASSEMBLY_API_URL` | (optional) | 의회·법률정보 포털 검색 엔드포인트 URL |
| `ASSEMBLY_API_QUERY_PARAM` | `search` | 질문을 전달할 쿼리 파라미터 이름 |
| `ASSEMBLY_API_TIMEOUT` | `10.0` | 법령 API 호출 타임아웃(초) |

> Note: the Google OAuth flow expects a valid access token issued by Google; no configuration is stored in this service.

## Setup

1. Install Python dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. Start MySQL using Docker (from the repository root):

   ```bash
   docker compose -f docker/docker-compose.yaml up -d
   docker compose -f docker/docker-compose.yaml logs -f mysql
   ```

   The database stores its data under `docker/docker-data/mysql`.

3. Launch the FastAPI server:

   ```bash
   uvicorn main:app --reload
   ```

   The API will be available at `http://localhost:8000` with interactive docs at `/docs` and `/redoc`. Database tables are created automatically during startup.

4. (Optional) Open the MLflow UI in another terminal to inspect logged metrics:

   ```bash
   mlflow ui --backend-store-uri data/mlruns
   ```

### Data Directories

- `data/uploads`: original files uploaded through the API
- `data/faiss`: FAISS index (`faiss_index.bin`) and chunk metadata (`metadata.json`)
- `data/mlruns`: MLflow tracking data
- `docker/docker-data/mysql`: persistent MySQL volume managed by Docker

## Using the API

### Upload a document

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@/path/to/sample.pdf"
```

### Ask a question with retrieval-augmented chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
        "message": "Summarise the onboarding policy.",
        "session_id": null,
        "conversation_history": []
      }'
```

Reuse the returned `session_id` for follow-up questions to preserve context.

If `ASSEMBLY_API_*` 환경 변수를 설정하면 같은 응답에 `related_laws`(질문과 연관된 법령 목록)와 `law_context`(LangGraph로 정리한 요약)가 추가로 포함됩니다. 이를 통해 LangGraph + RAG 파이프라인이 사내 문서 컨텍스트와 외부 의회·법률정보를 동시에 반영하도록 구성했습니다.

### Inspect sample requests

The `test_main.http` file contains ready-to-run HTTP requests for VS Code or the REST Client extension.

## API Surface

| Method | Path | Description |
| --- | --- | --- |
| GET | `/` | Service metadata and advertised features |
| GET | `/health` | Liveness probe |
| GET | `/architecture` | Current DDD layer summary |
| POST | `/documents/upload` | Upload and process a document (PDF, TXT, DOCX) |
| GET | `/documents` | List stored documents with processing status |
| GET | `/documents/{document_id}` | Retrieve document metadata |
| DELETE | `/documents/{document_id}` | Remove a document, its vectors, and file |
| GET | `/documents/statistics/overview` | Aggregate document ingestion metrics |
| POST | `/chat` | Send a message and receive a RAG answer |
| GET | `/chat/sessions` | List chat sessions |
| GET | `/chat/sessions/{session_id}/history` | Retrieve chat history for a session |
| DELETE | `/chat/sessions/{session_id}` | Remove a chat session and its messages |
| GET | `/chat/statistics` | Aggregate chat performance metrics |
| POST | `/auth/google` | Sign in with a Google OAuth access token |
| GET | `/auth/users` | List users stored in the system |
| GET | `/auth/users/{user_id}` | Fetch user details |
| DELETE | `/auth/users/{user_id}` | Delete a user |

## Observability and Metrics

- Each document ingestion run logs metadata, chunk counts, and processing durations to MLflow.
- Chat interactions record retrieval, generation, and total latency along with similarity scores.
- SQLAlchemy emits SQL statements via `echo=True` in `app/db/database.py`; adjust if quieter logs are required.

## Troubleshooting

- **Database connection errors**: confirm the MySQL container is running and the `.env` connection variables match the Compose service.
- **OpenAI API failures**: verify `OPENAI_API_KEY` is set and the host can reach the OpenAI API. Rate limits are logged under `data/mlruns`.
- **FAISS index missing**: the server initialises the index on first run. Ensure the process has write access to `data/faiss`.

---

This README reflects the current project structure (`main.py` startup hooks call `create_tables()`), so rerun the application after changing dependencies or configuration files.
