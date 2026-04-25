import json
import os
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from app.config import settings
from app.core.logger import logger


@dataclass
class VectorRecord:
    doc_id: str
    doc_name: str
    chunk_index: int
    text: str
    vector: List[float]
    metadata: Dict[str, Any]


@dataclass
class SearchResult:
    doc_id: str
    doc_name: str
    chunk_index: int
    text: str
    score: float
    metadata: Dict[str, Any]


class VectorStore:
    def __init__(self, store_path: str = None):
        self.store_path = Path(store_path or settings.VECTOR_STORE_PATH)
        self.store_path.mkdir(parents=True, exist_ok=True)

        self.vectors_path = self.store_path / "vectors.json"
        self.index_path = self.store_path / "index.json"
        self.records: List[VectorRecord] = []
        self._index: Dict[str, List[int]] = {}

        self._load()

    def _load(self):
        if self.vectors_path.exists():
            try:
                with open(self.vectors_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.records = [VectorRecord(**r) for r in data.get("records", [])]
                    self._build_index()
                    logger.info(f"Loaded {len(self.records)} vector records")
            except Exception as e:
                logger.warning(f"Failed to load vector store: {e}")
                self.records = []

    def _save(self):
        try:
            data = {
                "records": [asdict(r) for r in self.records]
            }
            with open(self.vectors_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.records)} vector records")
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")
            raise

    def _build_index(self):
        self._index = {}
        for i, record in enumerate(self.records):
            doc_id = record.doc_id
            if doc_id not in self._index:
                self._index[doc_id] = []
            self._index[doc_id].append(i)

    def add(self, record: VectorRecord):
        self.records.append(record)
        self._build_index()

    def add_batch(self, records: List[VectorRecord]):
        self.records.extend(records)
        self._build_index()

    def get_by_doc_id(self, doc_id: str) -> List[VectorRecord]:
        indices = self._index.get(doc_id, [])
        return [self.records[i] for i in indices]

    def remove_by_doc_id(self, doc_id: str):
        self.records = [r for r in self.records if r.doc_id != doc_id]
        self._build_index()

    def list_documents(self) -> List[Dict]:
        docs = {}
        for record in self.records:
            if record.doc_id not in docs:
                docs[record.doc_id] = {
                    "doc_id": record.doc_id,
                    "doc_name": record.doc_name,
                    "chunk_count": 0
                }
            docs[record.doc_id]["chunk_count"] += 1
        return list(docs.values())

    def clear(self):
        self.records = []
        self._index = {}
        self._save()

    def save(self):
        self._save()

    @property
    def count(self) -> int:
        return len(self.records)
