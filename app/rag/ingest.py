# app/rag/ingest.py

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

from sentence_transformers import SentenceTransformer

from app.rag.chroma_client import get_or_create_collection


# Cache model in-process
_model: Optional[SentenceTransformer] = None


def get_embedder(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(model_name)
    return _model


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> List[str]:
    """
    Simple character-based chunking (works well enough for v1).
    Later you can replace with token-based splitting.
    """
    text = (text or "").strip()
    if not text:
        return []

    chunks: List[str] = []
    i = 0
    while i < len(text):
        end = min(len(text), i + chunk_size)
        chunks.append(text[i:end])
        i = end - overlap
        if i < 0:
            i = 0
        if end == len(text):
            break
    return chunks


def _stable_id(collection: str, source_id: str, idx: int, chunk: str) -> str:
    h = hashlib.sha1(f"{collection}|{source_id}|{idx}|{chunk}".encode("utf-8")).hexdigest()
    return h


def ingest_documents(
    *,
    collection: str,
    docs: List[Dict[str, Any]],
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    chunk_size: int = 800,
    overlap: int = 120,
) -> Dict[str, Any]:
    """
    docs elements:
      {
        "text": "...",
        "source_id": "optional stable id",
        "metadata": {...}
      }
    """
    col = get_or_create_collection(collection)
    embedder = get_embedder(embedding_model)

    all_texts: List[str] = []
    all_ids: List[str] = []
    all_metas: List[Dict[str, Any]] = []

    total_chunks = 0

    for d_i, d in enumerate(docs):
        text = (d.get("text") or "").strip()
        if not text:
            continue

        source_id = (d.get("source_id") or f"doc-{d_i}").strip()
        metadata = d.get("metadata") or {}

        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        for c_i, chunk in enumerate(chunks):
            cid = _stable_id(collection, source_id, c_i, chunk)
            meta = {
                **metadata,
                "source_id": source_id,
                "chunk_index": c_i,
                "collection": collection,
            }
            all_ids.append(cid)
            all_texts.append(chunk)
            all_metas.append(meta)

        total_chunks += len(chunks)

    if not all_texts:
        return {"added": 0, "skipped": len(docs), "collection": collection}

    # Embed
    embeddings = embedder.encode(all_texts, normalize_embeddings=True).tolist()

    # Upsert (Chroma add will error on duplicate ids; so we delete-then-add for stability)
    # For v1, we try delete(ids) then add. If delete fails, we still attempt add.
    try:
        col.delete(ids=all_ids)
    except Exception:
        pass

    col.add(
        ids=all_ids,
        documents=all_texts,
        embeddings=embeddings,
        metadatas=all_metas,
    )

    return {
        "collection": collection,
        "documents_received": len(docs),
        "chunks_added": total_chunks,
        "ids_added": len(all_ids),
        "embedding_model": embedding_model,
        "chunk_size": chunk_size,
        "overlap": overlap,
    }
