<div align="center">

# Learnly QA Tool

**AI-powered vendor questionnaire automation using Retrieval-Augmented Generation**

[![Live Demo](https://img.shields.io/badge/Live_Demo-Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://web-production-feecc.up.railway.app/)
[![GitHub](https://img.shields.io/badge/Source_Code-GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Rajvardhan00/learnly-qa-tool)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

---

*Built as a GTM Engineering internship take-home assignment for a fictional EdTech SaaS company, Learnly — a learning management system for universities.*

</div>

---

## Overview

Learnly QA Tool eliminates manual effort in completing vendor security questionnaires. Upload your company's reference documents, upload a questionnaire, and the system automatically generates grounded, citation-backed answers using a RAG pipeline powered by LLaMA 3.3-70B.

Every answer is traceable to a specific source document — the system will never hallucinate or fabricate information not present in your references.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser (Frontend)                    │
│              Vanilla JS · Single HTML file · JWT Auth        │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP / REST
┌───────────────────────────▼─────────────────────────────────┐
│                      FastAPI Backend                         │
├──────────────┬─────────────────────┬────────────────────────┤
│   SQLite DB  │   RAG Pipeline      │   Groq / LLaMA API     │
│  SQLAlchemy  │  TF-IDF + Cosine    │   llama-3.3-70b        │
│  JWT / bcrypt│  Similarity Search  │   via httpx (REST)     │
└──────────────┴─────────────────────┴────────────────────────┘
```

---

## How It Works

### 1. Document Ingestion
Reference documents (PDF, DOCX, TXT) are uploaded and chunked into 350-word segments with 50-word overlap to preserve context across boundaries. Chunks are stored as JSON in SQLite.

### 2. Retrieval (RAG)
When a question is submitted, a TF-IDF vectorizer converts both the question and all stored chunks into term-frequency vectors. Cosine similarity scores each chunk against the question, and the top 3 most relevant chunks are retrieved.

### 3. AI Generation
The retrieved chunks are passed to LLaMA 3.3-70B via the Groq REST API with a strict system prompt:

> *"Answer ONLY using the provided reference excerpts. If the answer cannot be found, return not\_found: true."*

The model returns structured JSON containing the answer, source citations, confidence score, and evidence snippet.

### 4. Output
Answers are stored in SQLite, displayed in the UI with confidence badges, and exportable as a formatted DOCX file with citations and evidence.

---

## Workflow

```
Upload Reference Docs          Upload Questionnaire
       │                               │
       ▼                               ▼
  Parse & Chunk              Parse Questions (regex)
  (350w + 50w overlap)       (numbered / Q-prefixed)
       │                               │
       └──────────────┬────────────────┘
                      ▼
            For each question:
                      │
          ┌───────────▼───────────┐
          │   TF-IDF Vectorizer   │
          │   Cosine Similarity   │
          │   Top 3 Chunks        │
          └───────────┬───────────┘
                      │
          ┌───────────▼───────────┐
          │   Groq / LLaMA 3.3   │
          │   Structured JSON     │
          │   answer + citations  │
          └───────────┬───────────┘
                      │
          ┌───────────▼───────────┐
          │   Store in SQLite     │
          │   Display in UI       │
          │   Export to DOCX      │
          └───────────────────────┘
```

---

## Features

| Feature | Description |
|---|---|
| RAG Pipeline | TF-IDF chunking + cosine similarity retrieval grounded strictly in uploaded docs |
| AI Generation | LLaMA 3.3-70B via Groq API returning structured JSON with citations |
| Confidence Scores | High / Mid / Low badges per answer (color-coded) |
| Evidence Snippets | Top retrieved chunk excerpt shown below each answer |
| Not Found Detection | Returns "Not found in references" instead of hallucinating |
| JWT Authentication | Stateless token-based auth — each user sees only their own data |
| Inline Editing | Edit any answer directly in the UI with "edited" badge |
| Partial Regeneration | Select specific questions via checkbox and regenerate only those |
| Coverage Summary | Dashboard showing answered vs not-found counts per run |
| DOCX Export | Word document with citations, confidence, and evidence per answer |
| Run History | All previous questionnaire runs saved and accessible |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.11, Uvicorn |
| Database | SQLite via SQLAlchemy ORM |
| Authentication | JWT (python-jose) + bcrypt |
| AI Model | LLaMA 3.3-70B via Groq API (httpx REST) |
| RAG | TF-IDF + Cosine Similarity (scikit-learn) |
| File Parsing | PyMuPDF (PDF), python-docx (DOCX), UTF-8 (TXT) |
| Export | python-docx |
| Frontend | Vanilla JS, single HTML file |
| Deployment | Railway |

---

## Project Structure

```
learnly-qa-tool/
├── backend/
│   ├── main.py              # FastAPI app — all routes
│   ├── ai.py                # Groq REST API via httpx
│   ├── auth.py              # JWT authentication
│   ├── database.py          # SQLAlchemy models
│   ├── rag.py               # TF-IDF chunking + retrieval
│   ├── parser.py            # PDF/DOCX/TXT parsing + question extraction
│   ├── exporter.py          # DOCX export with citations
│   ├── reference_docs/      # Learnly source documents
│   └── sample_data/         # Sample vendor questionnaire
├── frontend/
│   └── index.html           # Complete UI (single file)
├── render.yaml
├── railway.toml
├── requirements.txt
└── .env.example
```

---

## Running Locally

### Prerequisites
- Python 3.11+
- Groq API key (free at [console.groq.com](https://console.groq.com))

### Setup

```bash
git clone https://github.com/Rajvardhan00/learnly-qa-tool.git
cd learnly-qa-tool

pip install -r requirements.txt
```

### Environment Variables

```bash
# Windows
set GROQ_API_KEY=your_groq_key_here
set SECRET_KEY=any-random-string

# Linux / Mac
export GROQ_API_KEY=your_groq_key_here
export SECRET_KEY=any-random-string
```

### Run

```bash
cd backend
python main.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq API key for LLaMA access |
| `SECRET_KEY` | Yes | JWT signing secret (any random string) |
| `DATABASE_URL` | No | Defaults to `sqlite:///./learnly.db` |
| `PORT` | No | Defaults to `8000` |

---

## Design Decisions

**Why TF-IDF over embeddings?**
TF-IDF requires no external embedding API, no additional cost, and works well for keyword-heavy security questionnaires where exact term matching matters. It also runs entirely in-process with no latency overhead.

**Why httpx directly instead of the Groq library?**
The `groq` Python library had version conflicts with `httpx` that caused connection errors in production. Calling the Groq REST API directly via `httpx` is simpler, more stable, and removes the dependency entirely.

**Why SQLite over PostgreSQL?**
For a single-user or low-traffic tool, SQLite eliminates infrastructure complexity. Railway's persistent disk ensures data survives restarts. The ORM abstraction (SQLAlchemy) makes migrating to PostgreSQL trivial if needed.

**Why a single HTML file for the frontend?**
No build step, no Node.js dependency, no bundler. The tool deploys and runs with zero frontend tooling — reducing operational complexity and making the project easier to audit.

---

<div align="center">

Built by [Raj Vardhan](https://github.com/Rajvardhan00)

</div>
