# app/api/routes_rag.py

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.rag.chroma_client import get_chroma_client
from app.rag.ingest import ingest_documents
from app.rag.query import rag_query


# IMPORTANT: this name must be `router`
router = APIRouter(prefix="/rag", tags=["RAG"])


class IngestDoc(BaseModel):
    text: str = Field(..., description="Document text to ingest")
    source_id: Optional[str] = Field(None, description="Stable source id (file name, url, host, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    collection: str = Field("iso27001", description="Chroma collection name")
    docs: List[IngestDoc]
    embedding_model: str = Field("sentence-transformers/all-MiniLM-L6-v2")
    chunk_size: int = Field(800, ge=200, le=4000)
    overlap: int = Field(120, ge=0, le=1000)


class QueryRequest(BaseModel):
    collection: str = Field("iso27001")
    query: str
    top_k: int = Field(5, ge=1, le=20)
    embedding_model: str = Field("sentence-transformers/all-MiniLM-L6-v2")
    where: Optional[Dict[str, Any]] = None


@router.get("/collections")
async def list_collections():
    client = get_chroma_client()
    cols = client.list_collections()
    return {"collections": [c.name for c in cols]}


@router.post("/ingest")
async def ingest(req: IngestRequest):
    return ingest_documents(
        collection=req.collection,
        docs=[d.model_dump() for d in req.docs],
        embedding_model=req.embedding_model,
        chunk_size=req.chunk_size,
        overlap=req.overlap,
    )


@router.post("/query")
async def query(req: QueryRequest):
    return rag_query(
        collection=req.collection,
        query=req.query,
        top_k=req.top_k,
        embedding_model=req.embedding_model,
        where=req.where,
    )
