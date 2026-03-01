# app/rag/chroma_client.py

from __future__ import annotations

import os
from functools import lru_cache
import chromadb


def _default_db_path() -> str:
    # project-root/storage/chroma_db
    # This file is located at app/rag/chroma_client.py, so go up 2 levels -> project root
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_dir, "storage", "chroma_db")


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    db_path = _default_db_path()
    os.makedirs(db_path, exist_ok=True)
    return chromadb.PersistentClient(path=db_path)


def get_or_create_collection(name: str):
    client = get_chroma_client()
    return client.get_or_create_collection(name=name)
