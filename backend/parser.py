import re
import fitz  # PyMuPDF
from docx import Document
from typing import List, Dict
import io


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes."""
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from plain text file."""
    return file_bytes.decode("utf-8", errors="ignore")


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Auto-detect file type and extract text."""
    fn = filename.lower()
    if fn.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif fn.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    elif fn.endswith(".txt"):
        return extract_text_from_txt(file_bytes)
    else:
        # Try txt as fallback
        return extract_text_from_txt(file_bytes)


def parse_questions(text: str) -> List[Dict]:
    """
    Parse a questionnaire text into individual questions.
    Handles multiple formats:
    - Numbered: "1. Question" or "1) Question" or "Q1: Question"
    - Lettered: "a. Question" or "A) Question"
    - Plain newline-separated questions ending with "?"
    """
    questions = []
    
    # Try numbered patterns first (most common)
    numbered_pattern = re.compile(
        r'(?:^|\n)\s*(?:Q\s*)?(\d+)[.):\s]+([^\n]+(?:\n(?!\s*(?:Q\s*)?\d+[.):\s])[^\n]*)*)',
        re.MULTILINE
    )
    
    matches = list(numbered_pattern.finditer(text))
    
    if matches and len(matches) >= 2:
        for match in matches:
            num = int(match.group(1))
            q_text = re.sub(r'\s+', ' ', match.group(2)).strip()
            if q_text and len(q_text) > 5:
                questions.append({"number": num, "text": q_text})
        return questions
    
    # Try line-by-line: lines ending with "?" or starting with question words
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    q_num = 1
    
    for line in lines:
        # Skip very short lines, headers
        if len(line) < 10:
            continue
        
        # Remove numbering prefix if present
        clean = re.sub(r'^(?:Q\s*)?\d+[.):\s]+', '', line).strip()
        clean = re.sub(r'^[a-zA-Z][.)]\s+', '', clean).strip()
        
        if not clean:
            continue
            
        # Include if it ends with ? OR is long enough to be a question
        if clean.endswith('?') or len(clean) > 30:
            questions.append({"number": q_num, "text": clean})
            q_num += 1
    
    return questions
