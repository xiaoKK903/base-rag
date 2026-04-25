import math
from typing import List, Optional
from dataclasses import dataclass
from app.config import settings
from app.core.logger import logger
from app.rag.vector_store import VectorStore, VectorRecord, SearchResult


class Retriever:
    def __init__(self, vector_store: VectorStore = None, top_k: int = None, min_score: float = None):
        self.vector_store = vector_store or VectorStore()
        self.top_k = top_k or settings.TOP_K
        self.min_score = min_score or settings.MIN_SCORE

    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if len(v1) != len(v2):
            logger.warning(f"Vector dimension mismatch: {len(v1)} vs {len(v2)}")
            return 0.0

        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def retrieve(self, query_vector: List[float], top_k: int = None, min_score: float = None) -> List[SearchResult]:
        k = top_k or self.top_k
        score_threshold = min_score or self.min_score

        if not self.vector_store.records:
            logger.warning("No records in vector store")
            return []

        scores = []
        for i, record in enumerate(self.vector_store.records):
            score = self.cosine_similarity(query_vector, record.vector)
            if score >= score_threshold:
                scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scores[:k]:
            record = self.vector_store.records[idx]
            results.append(SearchResult(
                doc_id=record.doc_id,
                doc_name=record.doc_name,
                chunk_index=record.chunk_index,
                text=record.text,
                score=score,
                metadata=record.metadata
            ))

        logger.info(f"Retrieved {len(results)} results (top_k={k}, min_score={score_threshold})")
        return results

    def retrieve_with_doc_filter(
        self,
        query_vector: List[float],
        doc_ids: List[str] = None,
        top_k: int = None,
        min_score: float = None
    ) -> List[SearchResult]:
        if not doc_ids:
            return self.retrieve(query_vector, top_k, min_score)

        original_records = self.vector_store.records
        filtered_records = [r for r in original_records if r.doc_id in doc_ids]

        self.vector_store.records = filtered_records
        try:
            results = self.retrieve(query_vector, top_k, min_score)
        finally:
            self.vector_store.records = original_records

        return results
