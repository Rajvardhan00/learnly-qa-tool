import json
import re
from typing import List, Tuple, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


def chunk_text(text: str, doc_name: str, chunk_size: int = 350, overlap: int = 50) -> List[Dict]:
    """Split document text into overlapping chunks."""
    # Clean text
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()
    chunks = []
    
    for i in range(0, max(1, len(words) - chunk_size + 1), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        if len(chunk_words) < 20:  # Skip very small trailing chunks
            continue
        chunks.append({
            "text": " ".join(chunk_words),
            "doc_name": doc_name,
            "start_word": i
        })
    
    # Always include at least one chunk
    if not chunks and words:
        chunks.append({
            "text": " ".join(words),
            "doc_name": doc_name,
            "start_word": 0
        })
    
    return chunks


def retrieve_chunks(question: str, all_chunks: List[Dict], top_k: int = 3) -> List[Tuple[Dict, float]]:
    """Retrieve most relevant chunks for a question using TF-IDF cosine similarity."""
    if not all_chunks:
        return []
    
    texts = [c["text"] for c in all_chunks]
    
    try:
        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=5000
        )
        all_texts = texts + [question]
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        
        question_vec = tfidf_matrix[-1]
        doc_vecs = tfidf_matrix[:-1]
        
        scores = cosine_similarity(question_vec, doc_vecs)[0]
        
        top_k_actual = min(top_k, len(all_chunks))
        top_indices = scores.argsort()[-top_k_actual:][::-1]
        
        results = [(all_chunks[i], float(scores[i])) for i in top_indices]
        return results
    except Exception as e:
        # Fallback: return first top_k chunks with score 0
        return [(c, 0.0) for c in all_chunks[:top_k]]


def compute_confidence(retrieval_scores: List[float], answer: str) -> float:
    """Compute confidence score from retrieval quality."""
    if not retrieval_scores:
        return 0.0
    
    # Base confidence from top retrieval score
    top_score = max(retrieval_scores)
    avg_score = sum(retrieval_scores) / len(retrieval_scores)
    
    # Penalize "not found" answers
    if "not found in references" in answer.lower():
        return 0.0
    
    # Weighted score: top score matters more
    raw = (top_score * 0.7) + (avg_score * 0.3)
    
    # Normalize to 0-1 range (TF-IDF cosine scores are already 0-1)
    confidence = min(1.0, raw * 2.5)  # scale up since TF-IDF scores tend to be low
    return round(confidence, 2)


def serialize_chunks(chunks: List[Dict]) -> str:
    return json.dumps(chunks)


def deserialize_chunks(chunks_json: str) -> List[Dict]:
    if not chunks_json:
        return []
    return json.loads(chunks_json)
