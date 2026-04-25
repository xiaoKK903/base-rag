from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
from app.core.logger import logger
from app.rag.vector_store import SearchResult
from app.rag.keyword_searcher import KeywordSearchResult, KeywordSearcher
from app.rag.rag_config import rag_config


@dataclass
class HybridSearchResult:
    doc_id: str
    doc_name: str
    chunk_index: int
    text: str
    final_score: float
    vector_score: float
    keyword_score: float
    matched_keywords: List[str]
    rank_before_rerank: int = -1
    rank_after_rerank: int = -1


@dataclass
class RerankResult:
    original_results: List[Dict]
    reranked_results: List[Dict]
    rank_changes: Dict[str, Tuple[int, int]]
    is_reranked: bool


class HybridSearcher:
    def __init__(self):
        self.keyword_searcher = KeywordSearcher()
        self._initialized = False

    def build_index_from_vectors(self, vector_records: List):
        documents = []
        for record in vector_records:
            documents.append({
                "doc_id": record.doc_id,
                "doc_name": record.doc_name,
                "chunk_index": record.chunk_index,
                "text": record.text
            })
        
        self.keyword_searcher.reset()
        self.keyword_searcher.add_documents(documents)
        self.keyword_searcher.build()
        self._initialized = True
        logger.info(f"Built keyword index from {len(documents)} chunks")

    def _normalize_scores(self, results: List, score_attr: str) -> List[Dict]:
        if not results:
            return []
        
        scores = [getattr(r, score_attr) for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        normalized = []
        for r in results:
            score = getattr(r, score_attr)
            if max_score == min_score:
                norm_score = 1.0
            else:
                norm_score = (score - min_score) / (max_score - min_score)
            
            normalized.append({
                "doc_id": r.doc_id,
                "doc_name": r.doc_name,
                "chunk_index": r.chunk_index,
                "text": r.text,
                "original_score": score,
                "normalized_score": norm_score,
                "matched_keywords": getattr(r, "matched_keywords", []),
                "metadata": getattr(r, "metadata", {})
            })
        
        return normalized

    def hybrid_search(
        self,
        vector_results: List[SearchResult],
        query: str,
        keywords: List[str] = None,
        vector_weight: float = None,
        keyword_weight: float = None,
        top_k: int = 10
    ) -> Tuple[List[HybridSearchResult], Dict[str, Any]]:
        v_weight = vector_weight if vector_weight is not None else rag_config.vector_weight
        k_weight = keyword_weight if keyword_weight is not None else rag_config.keyword_weight

        debug_info = {
            "vector_weight": v_weight,
            "keyword_weight": k_weight,
            "vector_results_count": len(vector_results),
            "keyword_results_count": 0,
            "hybrid_results_count": 0,
            "vector_details": [],
            "keyword_details": [],
            "hybrid_details": []
        }

        normalized_vector = self._normalize_scores(vector_results, "score")
        for item in normalized_vector:
            debug_info["vector_details"].append({
                "doc_id": item["doc_id"],
                "doc_name": item["doc_name"],
                "chunk_index": item["chunk_index"],
                "original_score": item["original_score"],
                "normalized_score": item["normalized_score"]
            })

        keyword_results = []
        if rag_config.enable_keyword_search and self._initialized:
            keyword_results = self.keyword_searcher.search(query, keywords, top_k * 2)
            debug_info["keyword_results_count"] = len(keyword_results)

        normalized_keyword = self._normalize_scores(keyword_results, "score")
        for item in normalized_keyword:
            debug_info["keyword_details"].append({
                "doc_id": item["doc_id"],
                "doc_name": item["doc_name"],
                "chunk_index": item["chunk_index"],
                "original_score": item["original_score"],
                "normalized_score": item["normalized_score"],
                "matched_keywords": item["matched_keywords"]
            })

        merged = defaultdict(lambda: {
            "vector_score": 0.0,
            "keyword_score": 0.0,
            "doc_name": "",
            "chunk_index": 0,
            "text": "",
            "matched_keywords": [],
            "metadata": {}
        })

        for item in normalized_vector:
            key = (item["doc_id"], item["chunk_index"])
            merged[key]["vector_score"] = item["normalized_score"]
            merged[key]["doc_name"] = item["doc_name"]
            merged[key]["chunk_index"] = item["chunk_index"]
            merged[key]["text"] = item["text"]
            merged[key]["metadata"] = item["metadata"]

        for item in normalized_keyword:
            key = (item["doc_id"], item["chunk_index"])
            merged[key]["keyword_score"] = item["normalized_score"]
            if not merged[key]["doc_name"]:
                merged[key]["doc_name"] = item["doc_name"]
                merged[key]["chunk_index"] = item["chunk_index"]
                merged[key]["text"] = item["text"]
            merged[key]["matched_keywords"] = item["matched_keywords"]

        hybrid_results = []
        for (doc_id, chunk_index), data in merged.items():
            v_score = data["vector_score"]
            k_score = data["keyword_score"]

            if rag_config.enable_hybrid_search:
                final_score = v_score * v_weight + k_score * k_weight
            else:
                final_score = v_score if v_score > 0 else k_score

            hybrid_results.append(HybridSearchResult(
                doc_id=doc_id,
                doc_name=data["doc_name"],
                chunk_index=data["chunk_index"],
                text=data["text"],
                final_score=final_score,
                vector_score=v_score,
                keyword_score=k_score,
                matched_keywords=data["matched_keywords"]
            ))

        hybrid_results.sort(key=lambda x: x.final_score, reverse=True)

        for i, result in enumerate(hybrid_results):
            debug_info["hybrid_details"].append({
                "doc_id": result.doc_id,
                "doc_name": result.doc_name,
                "chunk_index": result.chunk_index,
                "vector_score": result.vector_score,
                "keyword_score": result.keyword_score,
                "final_score": result.final_score,
                "matched_keywords": result.matched_keywords,
                "rank_before_rerank": i + 1
            })

        debug_info["hybrid_results_count"] = len(hybrid_results)

        return hybrid_results[:top_k], debug_info


class Reranker:
    def __init__(self):
        pass

    def rerank(
        self,
        results: List[HybridSearchResult],
        query: str,
        top_k: int = None
    ) -> Tuple[List[HybridSearchResult], RerankResult]:
        k = top_k or rag_config.rerank_top_k

        original_ranking = {
            (r.doc_id, r.chunk_index): i + 1
            for i, r in enumerate(results)
        }

        rerank_debug = RerankResult(
            original_results=[],
            reranked_results=[],
            rank_changes={},
            is_reranked=False
        )

        for i, r in enumerate(results):
            rerank_debug.original_results.append({
                "doc_id": r.doc_id,
                "doc_name": r.doc_name,
                "chunk_index": r.chunk_index,
                "score": r.final_score,
                "rank": i + 1
            })

        if not rag_config.enable_reranking:
            for r in results:
                r.rank_before_rerank = original_ranking.get((r.doc_id, r.chunk_index), -1)
                r.rank_after_rerank = r.rank_before_rerank

            for i, r in enumerate(results[:k]):
                rerank_debug.reranked_results.append({
                    "doc_id": r.doc_id,
                    "doc_name": r.doc_name,
                    "chunk_index": r.chunk_index,
                    "score": r.final_score,
                    "rank_before": r.rank_before_rerank,
                    "rank_after": r.rank_after_rerank
                })

            return results[:k], rerank_debug

        reranked = self._simple_rerank(results, query)

        for i, r in enumerate(reranked):
            r.rank_before_rerank = original_ranking.get((r.doc_id, r.chunk_index), -1)
            r.rank_after_rerank = i + 1

            key = f"{r.doc_id}:{r.chunk_index}"
            rerank_debug.rank_changes[key] = (r.rank_before_rerank, r.rank_after_rerank)

            rerank_debug.reranked_results.append({
                "doc_id": r.doc_id,
                "doc_name": r.doc_name,
                "chunk_index": r.chunk_index,
                "score": r.final_score,
                "rank_before": r.rank_before_rerank,
                "rank_after": r.rank_after_rerank
            })

        rerank_debug.is_reranked = True

        return reranked[:k], rerank_debug

    def _simple_rerank(
        self,
        results: List[HybridSearchResult],
        query: str
    ) -> List[HybridSearchResult]:
        query_lower = query.lower()
        query_words = set(query_lower.split())

        def compute_rerank_score(result: HybridSearchResult) -> float:
            base_score = result.final_score
            
            text_lower = result.text.lower()
            
            exact_match_bonus = 0.0
            if query_lower in text_lower:
                exact_match_bonus = 0.3
            
            keyword_bonus = 0.0
            for word in query_words:
                if len(word) >= 2 and word in text_lower:
                    keyword_bonus += 0.05
            
            length_penalty = 1.0
            text_len = len(result.text)
            if text_len < 50:
                length_penalty = 0.8
            elif text_len > 500:
                length_penalty = 0.95
            
            final_score = (base_score + exact_match_bonus + keyword_bonus) * length_penalty
            
            return final_score

        reranked = sorted(
            results,
            key=compute_rerank_score,
            reverse=True
        )

        return reranked
