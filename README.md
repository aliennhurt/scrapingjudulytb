
# YouTube Winning Pattern Detector - Backend

## Overview
FastAPI backend for collecting YouTube video data and generating winning title templates using AgentBay Browser Use and OpenAI.

## Tech Stack
-   **Language**: Python 3.11
-   **Framework**: FastAPI
-   **Database**: Supabase Postgres (SQLAlchemy 2.x)
-   **Automation**: AgentBay SDK + Playwright (CDP)
-   **AI**: OpenAI-compatible LLM
-   **Deployment**: Docker (EasyPanel compatible)

## Setup

### Prerequisites
-   Docker & Docker Compose
-   Supabase Project
-   AgentBay Account (API Key)
-   OpenAI API Key

### Database Setup (Supabase)
The application will attempt to create tables on startup. Alternatively, you can run the SQL schema manually:
1.  Go to your Supabase Project Dashboard.
2.  Navigate to the **SQL Editor** (sidebar).
3.  Click **New query**.
4.  Copy the contents of `supabase_schema.sql` and paste it into the editor.
5.  Click **Run**.

### Local Development

1.  **Clone Request**:
    ```bash
    git clone <repo_url>
    cd scrapingjudulytb
    ```

2.  **Environment Variables**:
    Create a `.env` file in the root directory:
    ```env
    DATABASE_URL=postgresql://user:password@host:port/dbname
    AGENTBAY_API_KEY=your_agentbay_key
    OPENAI_API_KEY=your_openai_key
    # Optional
    OPENAI_MODEL=gpt-3.5-turbo
    ```

3.  **Run with Docker Compose**:
    ```bash
    docker-compose up --build
    ```
    The API will be available at `http://localhost:8000`.
    Docs: `http://localhost:8000/docs`

### Deployment (EasyPanel)

1.  **Project Type**: app (Docker)
2.  **Image**: Use "Build from Source" or point to your GitHub repo.
3.  **Build Command**: Dockerfile is provided in root.
4.  **Environment**: Add the variables from `.env` to the EasyPanel environment configuration.
5.  **Port**: 8000

## API Usage

### 1. Start Collection
**POST** `/api/collect/youtube`
```json
{
  "keyword": "n8n automation",
  "force_refresh": false
}
```

### 2. Check Status
**GET** `/api/collect/status/{job_id}`

## Project Structure
-   `app/api`: API Endpoints
-   `app/services`: Logic for AgentBay and AI
-   `app/db`: Database models and session
-   `app/utils`: Helpers (View parser)
