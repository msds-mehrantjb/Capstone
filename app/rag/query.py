# app/rag/query.py

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer

from app.rag.chroma_client import get_or_create_collection
from app.rag.ingest import get_embedder


def rag_query(
    *,
    collection: str,
    query: str,
    top_k: int = 5,
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    where: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    col = get_or_create_collection(collection)

    q = (query or "").strip()
    if not q:
        return {"collection": collection, "query": query, "results": []}

    embedder: SentenceTransformer = get_embedder(embedding_model)
    q_emb = embedder.encode(q, normalize_embeddings=True).tolist()

    res = col.query(
        query_embeddings=[q_emb],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances", "ids"],
    )

    # Chroma returns lists-of-lists (one per query)
    out: List[Dict[str, Any]] = []
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    for i in range(len(ids)):
        out.append(
            {
                "id": ids[i],
                "document": docs[i],
                "metadata": metas[i],
                "distance": dists[i],
            }
        )

    return {
        "collection": collection,
        "query": q,
        "top_k": top_k,
        "where": where,
        "results": out,
        "embedding_model": embedding_model,
    }
