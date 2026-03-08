import os
import sys

# Ensure backend directory is in path for Railway (/app/backend) and local
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import json
from datetime import timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, create_tables, User, ReferenceDoc, QuestionnaireRun, QAItem
from auth import hash_password, verify_password, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from rag import chunk_text, retrieve_chunks, serialize_chunks, deserialize_chunks
from parser import extract_text, parse_questions
from ai import generate_answer
from exporter import export_to_docx

app = FastAPI(title="Learnly QA Tool", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
_root_dir = os.path.join(_backend_dir, "..", "frontend")
FRONTEND_DIR = os.path.abspath(_root_dir)
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
def startup():
    create_tables()


# ── Pydantic models ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class EditAnswerRequest(BaseModel):
    answer: str

class RegenerateRequest(BaseModel):
    qa_item_ids: List[int]


# ── Auth ─────────────────────────────────────────────────────────────────────

@app.post("/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer",
            "user": {"email": user.email, "full_name": user.full_name}}


@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer",
            "user": {"email": user.email, "full_name": user.full_name}}


@app.get("/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return {"email": current_user.email, "full_name": current_user.full_name}


# ── Reference Docs ────────────────────────────────────────────────────────────

@app.get("/reference-docs")
def list_reference_docs(db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    docs = db.query(ReferenceDoc).filter(ReferenceDoc.user_id == current_user.id).all()
    return [{"id": d.id, "filename": d.filename, "created_at": str(d.created_at)} for d in docs]


@app.post("/reference-docs/upload")
async def upload_reference_doc(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    file_bytes = await file.read()
    content = extract_text(file_bytes, file.filename)
    if not content.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")
    chunks = chunk_text(content, file.filename)
    doc = ReferenceDoc(
        user_id=current_user.id,
        filename=file.filename,
        content=content,
        chunks_json=serialize_chunks(chunks)
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"id": doc.id, "filename": doc.filename, "chunks": len(chunks)}


@app.delete("/reference-docs/{doc_id}")
def delete_reference_doc(doc_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    doc = db.query(ReferenceDoc).filter(
        ReferenceDoc.id == doc_id, ReferenceDoc.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    return {"ok": True}


# ── Runs ──────────────────────────────────────────────────────────────────────

@app.get("/runs")
def list_runs(db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    runs = db.query(QuestionnaireRun).filter(
        QuestionnaireRun.user_id == current_user.id
    ).order_by(QuestionnaireRun.created_at.desc()).all()
    return [
        {
            "id": r.id, "filename": r.filename, "status": r.status,
            "total_questions": r.total_questions,
            "answered_count": r.answered_count,
            "not_found_count": r.not_found_count,
            "created_at": str(r.created_at)
        }
        for r in runs
    ]


@app.post("/runs/upload")
async def upload_questionnaire(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    file_bytes = await file.read()
    content = extract_text(file_bytes, file.filename)
    if not content.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")
    questions = parse_questions(content)
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found in document")
    run = QuestionnaireRun(
        user_id=current_user.id,
        filename=file.filename,
        status="pending",
        total_questions=len(questions)
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    for q in questions:
        item = QAItem(run_id=run.id,
                      question_number=q["number"],
                      question_text=q["text"])
        db.add(item)
    db.commit()
    return {
        "run_id": run.id,
        "filename": run.filename,
        "total_questions": len(questions),
        "questions": [{"number": q["number"], "text": q["text"]} for q in questions]
    }


@app.post("/runs/{run_id}/generate")
def generate_answers(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    run = db.query(QuestionnaireRun).filter(
        QuestionnaireRun.id == run_id,
        QuestionnaireRun.user_id == current_user.id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    ref_docs = db.query(ReferenceDoc).filter(ReferenceDoc.user_id == current_user.id).all()
    if not ref_docs:
        raise HTTPException(status_code=400,
                            detail="No reference documents uploaded. Please upload reference docs first.")

    all_chunks = []
    for doc in ref_docs:
        chunks = deserialize_chunks(doc.chunks_json)
        all_chunks.extend(chunks)

    items = db.query(QAItem).filter(QAItem.run_id == run_id).order_by(QAItem.question_number).all()
    run.status = "processing"
    db.commit()

    answered = 0
    not_found = 0
    for item in items:
        retrieved = retrieve_chunks(item.question_text, all_chunks, top_k=3)
        result = generate_answer(item.question_text, retrieved)
        item.answer = result["answer"]
        item.citations = json.dumps(result["citations"])
        item.evidence_snippet = result.get("evidence_snippet", "")
        item.confidence_score = result.get("confidence", 0.0)
        item.not_found = result.get("not_found", False)
        if item.not_found:
            not_found += 1
        else:
            answered += 1
        db.commit()

    run.status = "done"
    run.answered_count = answered
    run.not_found_count = not_found
    db.commit()
    return {"ok": True, "answered": answered, "not_found": not_found}


@app.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)):
    run = db.query(QuestionnaireRun).filter(
        QuestionnaireRun.id == run_id,
        QuestionnaireRun.user_id == current_user.id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    items = db.query(QAItem).filter(QAItem.run_id == run_id).order_by(QAItem.question_number).all()
    return {
        "id": run.id,
        "filename": run.filename,
        "status": run.status,
        "total_questions": run.total_questions,
        "answered_count": run.answered_count,
        "not_found_count": run.not_found_count,
        "created_at": str(run.created_at),
        "qa_items": [
            {
                "id": item.id,
                "question_number": item.question_number,
                "question_text": item.question_text,
                "answer": item.answer,
                "citations": json.loads(item.citations) if item.citations else [],
                "evidence_snippet": item.evidence_snippet,
                "confidence_score": item.confidence_score,
                "is_edited": item.is_edited,
                "not_found": item.not_found,
            }
            for item in items
        ]
    }


@app.patch("/runs/{run_id}/items/{item_id}")
def edit_answer(
    run_id: int,
    item_id: int,
    req: EditAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(QAItem).join(QuestionnaireRun).filter(
        QAItem.id == item_id,
        QAItem.run_id == run_id,
        QuestionnaireRun.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.answer = req.answer
    item.is_edited = True
    item.not_found = "not found in references" in req.answer.lower()
    db.commit()
    return {"ok": True}


@app.post("/runs/{run_id}/regenerate")
def regenerate_selected(
    run_id: int,
    req: RegenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    run = db.query(QuestionnaireRun).filter(
        QuestionnaireRun.id == run_id,
        QuestionnaireRun.user_id == current_user.id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    ref_docs = db.query(ReferenceDoc).filter(ReferenceDoc.user_id == current_user.id).all()
    if not ref_docs:
        raise HTTPException(status_code=400, detail="No reference documents found")

    all_chunks = []
    for doc in ref_docs:
        chunks = deserialize_chunks(doc.chunks_json)
        all_chunks.extend(chunks)

    items = db.query(QAItem).filter(
        QAItem.run_id == run_id,
        QAItem.id.in_(req.qa_item_ids)
    ).all()

    for item in items:
        retrieved = retrieve_chunks(item.question_text, all_chunks, top_k=3)
        result = generate_answer(item.question_text, retrieved)
        item.answer = result["answer"]
        item.citations = json.dumps(result["citations"])
        item.evidence_snippet = result.get("evidence_snippet", "")
        item.confidence_score = result.get("confidence", 0.0)
        item.not_found = result.get("not_found", False)
        item.is_edited = False
        db.commit()

    all_items = db.query(QAItem).filter(QAItem.run_id == run_id).all()
    run.answered_count = sum(1 for i in all_items if not i.not_found and i.answer)
    run.not_found_count = sum(1 for i in all_items if i.not_found)
    db.commit()
    return {"ok": True, "regenerated": len(items)}


@app.get("/runs/{run_id}/export")
def export_run(run_id: int, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    run = db.query(QuestionnaireRun).filter(
        QuestionnaireRun.id == run_id,
        QuestionnaireRun.user_id == current_user.id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    items = db.query(QAItem).filter(QAItem.run_id == run_id).order_by(QAItem.question_number).all()
    docx_bytes = export_to_docx(run, items)
    safe_name = run.filename.rsplit(".", 1)[0]
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_answers.docx"'}
    )


@app.get("/")
def root():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Learnly QA Tool API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    os.chdir(_backend_dir)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
