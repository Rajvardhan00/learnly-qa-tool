import json
import os
import re
import time
from typing import List, Tuple, Dict


SYSTEM_PROMPT = """You are a compliance assistant for Learnly, a SaaS LMS platform.
Answer questions using ONLY the provided reference excerpts.
If the answer is not in the excerpts, respond with "Not found in references."

Respond ONLY with valid JSON, no markdown, no extra text:
{
  "answer": "Your answer here, or 'Not found in references.' if not supported",
  "citations": ["Document Name 1"],
  "confidence": 0.85
}
Confidence: 0.9-1.0 = directly stated, 0.7-0.89 = implied, 0.5-0.69 = partial, below 0.5 = not found"""


def generate_answer(question: str, retrieved_chunks: list) -> dict:
    if not retrieved_chunks:
        return {
            "answer": "Not found in references.",
            "citations": [],
            "evidence_snippet": "",
            "confidence": 0.0,
            "not_found": True
        }

    context_parts = []
    for chunk, score in retrieved_chunks:
        context_parts.append(f"[Source: {chunk['doc_name']}]\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_parts)
    best_chunk = retrieved_chunks[0][0]
    evidence_snippet = best_chunk["text"][:250].strip()
    if len(best_chunk["text"]) > 250:
        evidence_snippet += "..."

    try:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")

        # Use httpx directly to avoid any Groq client version issues
        import httpx

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "max_tokens": 500,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Reference excerpts:\n{context}\n\nQuestion: {question}\n\nRespond ONLY with valid JSON."
                }
            ]
        }

        time.sleep(3)  # avoid rate limiting

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        raw_text = data["choices"][0]["message"]["content"].strip()

        # Strip markdown fences if present
        raw_text = re.sub(r'^```json\s*', '', raw_text)
        raw_text = re.sub(r'^```\s*', '', raw_text)
        raw_text = re.sub(r'\s*```$', '', raw_text)

        result = json.loads(raw_text)
        answer = result.get("answer", "Not found in references.")
        citations = result.get("citations", [])
        ai_confidence = float(result.get("confidence", 0.5))
        not_found = isinstance(answer, str) and "not found in references" in answer.lower()

        return {
            "answer": answer,
            "citations": citations,
            "evidence_snippet": "" if not_found else evidence_snippet,
            "confidence": 0.0 if not_found else ai_confidence,
            "not_found": not_found
        }

    except json.JSONDecodeError:
        return {
            "answer": "Not found in references.",
            "citations": [],
            "evidence_snippet": "",
            "confidence": 0.0,
            "not_found": True
        }
    except Exception as e:
        return {
            "answer": f"Error generating answer: {str(e)}",
            "citations": [],
            "evidence_snippet": "",
            "confidence": 0.0,
            "not_found": True
        }
