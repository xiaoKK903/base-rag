import os
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from app.config import settings
from app.core.logger import logger
from app.rag.chunker import TextChunker, DocumentChunk
from app.rag.embedding import EmbeddingService
from app.rag.vector_store import VectorStore, VectorRecord, SearchResult
from app.rag.retriever import Retriever
from app.rag.llm_service import LLMService, LLMResponse
from app.rag.rag_config import rag_config
from app.rag.query_rewriter import QueryRewriter, RewriteResult
from app.rag.keyword_searcher import KeywordSearcher
from app.rag.hybrid_searcher import (
    HybridSearcher, HybridSearchResult, 
    Reranker, RerankResult
)


@dataclass
class UploadResult:
    doc_id: str
    doc_name: str
    chunk_count: int
    success: bool
    message: str = ""


@dataclass
class RAGDebugInfo:
    original_query: str = ""
    rewritten_query: str = ""
    is_rewritten: bool = False
    keywords: List[str] = field(default_factory=list)
    
    vector_results: List[Dict] = field(default_factory=list)
    keyword_results: List[Dict] = field(default_factory=list)
    hybrid_results: List[Dict] = field(default_factory=list)
    reranked_results: List[Dict] = field(default_factory=list)
    
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    
    feature_status: Dict[str, bool] = field(default_factory=dict)


@dataclass
class RAGQueryResult:
    query: str
    results: List[SearchResult]
    context: str
    answer: str
    metadata: Dict[str, Any]
    debug_info: Optional[RAGDebugInfo] = None


class RAGService:
    def __init__(self):
        self.chunker = TextChunker()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.retriever = Retriever(self.vector_store)
        self.llm_service = LLMService()
        
        self.query_rewriter = QueryRewriter(self.llm_service)
        self.hybrid_searcher = HybridSearcher()
        self.reranker = Reranker()

        self.docs_path = Path(settings.DOCUMENTS_PATH)
        self.docs_path.mkdir(parents=True, exist_ok=True)
        
        self._keyword_index_built = False

    def _rebuild_keyword_index(self):
        if self.vector_store.records:
            self.hybrid_searcher.build_index_from_vectors(self.vector_store.records)
            self._keyword_index_built = True

    async def upload_document(
        self,
        content: str,
        filename: str,
        doc_id: str = None
    ) -> UploadResult:
        if not content or not content.strip():
            return UploadResult(
                doc_id="",
                doc_name=filename,
                chunk_count=0,
                success=False,
                message="文档内容为空"
            )

        if not doc_id:
            doc_id = hashlib.md5(content.encode()).hexdigest()[:16]

        existing_docs = self.vector_store.list_documents()
        for doc in existing_docs:
            if doc["doc_id"] == doc_id:
                return UploadResult(
                    doc_id=doc_id,
                    doc_name=filename,
                    chunk_count=0,
                    success=True,
                    message="文档已存在"
                )

        chunks = self.chunker.chunk_text(content, doc_id, filename)
        if not chunks:
            return UploadResult(
                doc_id=doc_id,
                doc_name=filename,
                chunk_count=0,
                success=False,
                message="无法提取有效文本块"
            )

        logger.info(f"Document split into {len(chunks)} chunks")

        embedding_results = await self.embedding_service.embed_batch(
            [chunk.text for chunk in chunks]
        )

        records = []
        for i, chunk in enumerate(chunks):
            embedding = embedding_results[i] if i < len(embedding_results) else None
            if embedding:
                record = VectorRecord(
                    doc_id=doc_id,
                    doc_name=filename,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    vector=embedding.vector,
                    metadata={
                        "start_pos": chunk.start_pos,
                        "end_pos": chunk.end_pos,
                        "embedding_model": embedding.model
                    }
                )
                records.append(record)

        self.vector_store.add_batch(records)
        self.vector_store.save()

        doc_file = self.docs_path / f"{doc_id}.txt"
        with open(doc_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        self._rebuild_keyword_index()

        logger.info(f"Document {filename} uploaded with {len(records)} vectors")

        return UploadResult(
            doc_id=doc_id,
            doc_name=filename,
            chunk_count=len(records),
            success=True,
            message=f"成功上传，生成 {len(records)} 个向量块"
        )

    async def upload_file(self, file_path: str) -> UploadResult:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            filename = os.path.basename(file_path)
            return await self.upload_document(content, filename)
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return UploadResult(
                doc_id="",
                doc_name=os.path.basename(file_path),
                chunk_count=0,
                success=False,
                message=f"上传失败: {str(e)}"
            )

    async def query(
        self,
        question: str,
        top_k: int = None,
        min_score: float = None,
        doc_ids: List[str] = None
    ) -> RAGQueryResult:
        if not question or not question.strip():
            return RAGQueryResult(
                query="",
                results=[],
                context="",
                answer="",
                metadata={"error": "问题为空"}
            )

        debug_info = RAGDebugInfo()
        debug_info.feature_status = rag_config.get_feature_status()
        debug_info.original_query = question

        effective_query = question
        keywords = []

        if rag_config.enable_query_rewrite:
            logger.info(f"Rewriting query: {question}")
            rewrite_result = await self.query_rewriter.rewrite(question)
            debug_info.rewritten_query = rewrite_result.rewritten_query
            debug_info.is_rewritten = rewrite_result.is_rewritten
            debug_info.keywords = rewrite_result.keywords
            
            if rewrite_result.is_rewritten:
                effective_query = rewrite_result.rewritten_query
                logger.info(f"Query rewritten to: {effective_query}")
            
            keywords = rewrite_result.keywords

        query_embedding = await self.embedding_service.embed_single(effective_query)

        if doc_ids:
            vector_results = self.retriever.retrieve_with_doc_filter(
                query_vector=query_embedding.vector,
                doc_ids=doc_ids,
                top_k=top_k,
                min_score=min_score
            )
        else:
            vector_results = self.retriever.retrieve(
                query_vector=query_embedding.vector,
                top_k=top_k,
                min_score=min_score
            )

        for r in vector_results:
            debug_info.vector_results.append({
                "doc_id": r.doc_id,
                "doc_name": r.doc_name,
                "chunk_index": r.chunk_index,
                "text": r.text[:100] + "..." if len(r.text) > 100 else r.text,
                "score": r.score
            })

        if not self._keyword_index_built:
            self._rebuild_keyword_index()

        final_results: List[HybridSearchResult] = []
        rerank_result: Optional[RerankResult] = None

        if rag_config.enable_hybrid_search or rag_config.enable_keyword_search:
            k = top_k or settings.TOP_K
            
            hybrid_results, hybrid_debug = self.hybrid_searcher.hybrid_search(
                vector_results=vector_results,
                query=effective_query,
                keywords=keywords,
                top_k=k * 2
            )
            
            debug_info.hybrid_results = hybrid_debug.get("hybrid_details", [])
            debug_info.vector_results = hybrid_debug.get("vector_details", [])
            debug_info.keyword_results = hybrid_debug.get("keyword_details", [])
            debug_info.vector_weight = hybrid_debug.get("vector_weight", 0.7)
            debug_info.keyword_weight = hybrid_debug.get("keyword_weight", 0.3)
            
            if rag_config.enable_reranking:
                final_results, rerank_result = self.reranker.rerank(
                    hybrid_results,
                    effective_query,
                    top_k=k
                )
                
                debug_info.reranked_results = rerank_result.reranked_results
            else:
                final_results = hybrid_results[:k]
                for i, r in enumerate(final_results):
                    r.rank_before_rerank = i + 1
                    r.rank_after_rerank = i + 1
        else:
            final_results = []
            for i, r in enumerate(vector_results):
                final_results.append(HybridSearchResult(
                    doc_id=r.doc_id,
                    doc_name=r.doc_name,
                    chunk_index=r.chunk_index,
                    text=r.text,
                    final_score=r.score,
                    vector_score=r.score,
                    keyword_score=0.0,
                    matched_keywords=[],
                    rank_before_rerank=i + 1,
                    rank_after_rerank=i + 1
                ))

        search_results = []
        for r in final_results:
            search_results.append(SearchResult(
                doc_id=r.doc_id,
                doc_name=r.doc_name,
                chunk_index=r.chunk_index,
                text=r.text,
                score=r.final_score,
                metadata={
                    "vector_score": r.vector_score,
                    "keyword_score": r.keyword_score,
                    "matched_keywords": r.matched_keywords,
                    "rank_before_rerank": r.rank_before_rerank,
                    "rank_after_rerank": r.rank_after_rerank
                }
            ))

        context_parts = []
        for i, result in enumerate(search_results):
            context_parts.append(
                f"【文档 {i + 1}: {result.doc_name}】\n{result.text}"
            )

        context = "\n\n---\n\n".join(context_parts)

        logger.info(f"Calling LLM to generate answer for question: {question[:50]}...")
        llm_response = await self.llm_service.generate(question, context)
        logger.info(f"LLM generated answer, model: {llm_response.model}, tokens: {llm_response.tokens}")

        return RAGQueryResult(
            query=question,
            results=search_results,
            context=context,
            answer=llm_response.content,
            metadata={
                "total_results": len(search_results),
                "top_k": top_k or settings.TOP_K,
                "min_score": min_score or settings.MIN_SCORE,
                "doc_ids_filtered": doc_ids is not None,
                "llm_model": llm_response.model,
                "llm_tokens": llm_response.tokens,
                "used_query": effective_query,
                "keywords": keywords
            },
            debug_info=debug_info if rag_config.enable_debug else None
        )

    def list_documents(self) -> List[Dict[str, Any]]:
        return self.vector_store.list_documents()

    def get_document_count(self) -> int:
        return len(self.list_documents())

    def get_vector_count(self) -> int:
        return self.vector_store.count

    def delete_document(self, doc_id: str) -> bool:
        docs = self.list_documents()
        doc_exists = any(d["doc_id"] == doc_id for d in docs)

        if not doc_exists:
            return False

        self.vector_store.remove_by_doc_id(doc_id)
        self.vector_store.save()

        doc_file = self.docs_path / f"{doc_id}.txt"
        if doc_file.exists():
            doc_file.unlink()
        
        self._rebuild_keyword_index()

        logger.info(f"Document {doc_id} deleted")
        return True

    def clear_all(self) -> bool:
        self.vector_store.clear()

        for doc_file in self.docs_path.glob("*.txt"):
            doc_file.unlink()
        
        self._keyword_index_built = False

        logger.info("All documents cleared")
        return True

    async def close(self):
        await self.embedding_service.close()
        await self.llm_service.close()


rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
    return rag_service
