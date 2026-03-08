Here's the full README — copy everything below:

markdown<div align="center">

# Learnly QA Tool

**AI-powered vendor questionnaire automation using Retrieval-Augmented Generation**

[![Live Demo](https://img.shields.io/badge/Live_Demo-Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://web-production-feecc.up.railway.app/)
[![GitHub](https://img.shields.io/badge/Source_Code-GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Rajvardhan00/learnly-qa-tool)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

**Live at [https://web-production-feecc.up.railway.app/](https://web-production-feecc.up.railway.app/)**

</div>

---

## Overview

Learnly QA Tool eliminates manual effort in completing vendor security questionnaires. Upload your company's reference documents, upload a questionnaire, and the system automatically generates grounded, citation-backed answers using a RAG pipeline powered by LLaMA 3.3-70B.

Every answer is traceable to a specific source document. Questions with no matching evidence are explicitly flagged as unanswerable rather than guessed.

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
Reference documents (PDF, DOCX, TXT) are split into 350-word chunks with 50-word overlap to preserve context at boundaries. Chunks are stored as JSON in SQLite alongside their source filename.

### 2. Retrieval
When a question arrives, a TF-IDF vectorizer converts the question and every stored chunk into term-frequency vectors. Cosine similarity ranks all chunks against the question and returns the top 3.

### 3. Generation
The top chunks are sent to LLaMA 3.3-70B via the Groq REST API under a strict grounding constraint — the model answers only from the provided excerpts, or returns `not_found: true` if the answer is absent. The response is structured JSON containing the answer, citations, confidence score, and evidence snippet.

### 4. Storage and Export
Answers are persisted in SQLite per run, displayed in the UI with confidence badges, and exportable as a formatted DOCX file with citations and evidence included per question.

---

## Workflow
```
  Reference Documents                    Vendor Questionnaire
  (PDF / DOCX / TXT)                     (PDF / DOCX / TXT)
          │                                       │
          ▼                                       ▼
  Extract full text                      Extract full text
  Split into 350-word chunks             Regex isolates each question
  50-word overlap at boundaries          Handles numbered + Q-prefix formats
  Store chunks in SQLite                 Store questions linked to run ID
          │                                       │
          └─────────────────┬─────────────────────┘
                            │
               ─────────────────────────────
               Process each question in turn
               ─────────────────────────────
                            │
                            ▼
               TF-IDF vectorize the question
               TF-IDF vectorize all stored chunks
               Cosine similarity score each chunk
               Retrieve top 3 chunks by score
                            │
                            ▼
               Compose prompt:
                 system  — answer strictly from the excerpts below
                 user    — [chunk 1] [chunk 2] [chunk 3]
                           Question: {question text}
                            │
                            ▼
               POST  →  Groq REST API
               Model: llama-3.3-70b-versatile
                            │
               ┌────────────┴────────────┐
               │                         │
         Answer found               not_found: true
         + source citations         flagged in UI as unanswerable
         + confidence score         excluded from DOCX export
         + evidence snippet
               │
               ▼
        Persist to SQLite QAItem
        Render in UI with confidence badge
        Available for inline editing
        Exportable as formatted DOCX
```

---

## Features

| Feature | Description |
|---|---|
| RAG Pipeline | TF-IDF chunking + cosine similarity retrieval grounded strictly in uploaded docs |
| AI Generation | LLaMA 3.3-70B via Groq API returning structured JSON with citations |
| Confidence Scores | High / Mid / Low badges per answer (colour-coded) |
| Evidence Snippets | Top retrieved chunk excerpt shown below each answer |
| Not Found Detection | Explicitly flags unanswerable questions instead of hallucinating |
| JWT Authentication | Stateless token-based auth — each user sees only their own data |
| Inline Editing | Edit any answer directly in the UI with an "edited" badge |
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
├── railway.toml
├── requirements.txt
└── .env.example
```

---

## Running Locally

**Prerequisites:** Python 3.11+, Groq API key — free at [console.groq.com](https://console.groq.com)
```bash
git clone https://github.com/Rajvardhan00/learnly-qa-tool.git
cd learnly-qa-tool
pip install -r requirements.txt
```
```bash
# Windows
set GROQ_API_KEY=your_groq_key_here
set SECRET_KEY=any-random-string

# Linux / Mac
export GROQ_API_KEY=your_groq_key_here
export SECRET_KEY=any-random-string
```
```bash
cd backend
python main.py
# Open http://127.0.0.1:8000
```

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
TF-IDF requires no external embedding API and no additional cost. It performs well on keyword-heavy security questionnaires where exact term matching matters more than semantic distance, and runs entirely in-process with zero network latency.

**Why call the Groq API via httpx directly?**
The `groq` Python library had version conflicts with `httpx` that caused connection errors in production. Calling the REST endpoint directly removes the dependency entirely and is more stable across Python versions.

**Why SQLite over PostgreSQL?**
For a single-tenant tool, SQLite eliminates infrastructure overhead. The SQLAlchemy ORM abstraction makes swapping to PostgreSQL a one-line change if scale requires it.

**Why a single HTML file for the frontend?**
No build step, no Node.js, no bundler. The entire frontend ships as one file, making the project straightforward to deploy, audit, and fork.

---

<div align="center">

Built by [Raj Vardhan](https://github.com/Rajvardhan00)

</div>
