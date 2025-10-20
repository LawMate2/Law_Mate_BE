# FastAPI RAG Chatbot Server

## Prerequisites
- Docker 20+
- Python 3.11
- Poetry or `pip` (use `requirements.txt`)

## 1. Environment Setup
```bash
cp .env.example .env
```
Fill `OPENAI_API_KEY`, or add any remote DB credentials if you are not using the local MariaDB container.

## 2. MariaDB (Docker)
```bash
docker compose up -d
docker compose logs -f mariadb
```
- Data persists under `docker-data/mariadb`
- Place optional seed scripts (`*.sql` / `*.sh`) in `docker/mariadb/init`

## 3. FastAPI App
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## 4. Connection Details
- JDBC / SQLAlchemy URL: `mariadb+pymysql://appuser:apppw@127.0.0.1:3306/appdb`
- Test DB shell:
  ```bash
  docker exec -it mariadb-local mariadb -uappuser -papppw appdb
  ```

## 5. Useful Commands
- `docker compose down` - stop DB
- `uvicorn main:app` - production run
