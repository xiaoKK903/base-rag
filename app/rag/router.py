from fastapi import APIRouter, UploadFile, File, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.core import R, logger
from app.rag.service import get_rag_service
from app.rag.rag_config import rag_config, RAGConfig

rag_router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = None
    min_score: Optional[float] = None
    doc_ids: Optional[List[str]] = None


class RAGConfigUpdate(BaseModel):
    enable_query_rewrite: Optional[bool] = None
    enable_keyword_search: Optional[bool] = None
    enable_hybrid_search: Optional[bool] = None
    enable_reranking: Optional[bool] = None
    enable_debug: Optional[bool] = None
    vector_weight: Optional[float] = None
    keyword_weight: Optional[float] = None
    rerank_top_k: Optional[int] = None
    rerank_min_score: Optional[float] = None


@rag_router.post("/upload")
async def upload_document(
    file: UploadFile = File(..., description="要上传的文档文件（TXT/MD）")
):
    logger.info(f"上传文档: {file.filename}")

    allowed_types = ["text/plain", "text/markdown"]
    allowed_extensions = [".txt", ".md"]

    import os
    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""

    if file_ext not in allowed_extensions:
        return R.param_error(f"不支持的文件格式: {file_ext}，仅支持 .txt 和 .md")

    try:
        content = await file.read()
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            text_content = content.decode("gbk", errors="ignore")

        rag_service = get_rag_service()
        result = await rag_service.upload_document(text_content, file.filename or "untitled.txt")

        if result.success:
            return R.ok(data={
                "doc_id": result.doc_id,
                "doc_name": result.doc_name,
                "chunk_count": result.chunk_count,
                "total_docs": rag_service.get_document_count(),
                "total_vectors": rag_service.get_vector_count()
            }, message=result.message)
        else:
            return R.fail(message=result.message)

    except Exception as e:
        logger.error(f"上传文档失败: {e}")
        return R.fail(message=f"上传失败: {str(e)}")


@rag_router.post("/query")
async def query_rag(request: QueryRequest):
    logger.info(f"RAG查询: {request.question}")

    try:
        rag_service = get_rag_service()
        result = await rag_service.query(
            question=request.question,
            top_k=request.top_k,
            min_score=request.min_score,
            doc_ids=request.doc_ids
        )

        results_data = [
            {
                "doc_id": r.doc_id,
                "doc_name": r.doc_name,
                "chunk_index": r.chunk_index,
                "text": r.text,
                "score": r.score,
                "metadata": r.metadata
            }
            for r in result.results
        ]

        response_data = {
            "query": result.query,
            "results": results_data,
            "context": result.context,
            "answer": result.answer,
            "metadata": result.metadata
        }

        if result.debug_info is not None:
            response_data["debug_info"] = {
                "original_query": result.debug_info.original_query,
                "rewritten_query": result.debug_info.rewritten_query,
                "is_rewritten": result.debug_info.is_rewritten,
                "keywords": result.debug_info.keywords,
                "vector_results": result.debug_info.vector_results,
                "keyword_results": result.debug_info.keyword_results,
                "hybrid_results": result.debug_info.hybrid_results,
                "reranked_results": result.debug_info.reranked_results,
                "vector_weight": result.debug_info.vector_weight,
                "keyword_weight": result.debug_info.keyword_weight,
                "feature_status": result.debug_info.feature_status
            }

        return R.ok(data=response_data)

    except Exception as e:
        logger.error(f"RAG查询失败: {e}")
        return R.fail(message=f"查询失败: {str(e)}")


@rag_router.get("/query")
async def query_rag_get(
    question: str = Query(..., description="用户问题"),
    top_k: Optional[int] = Query(None, description="返回结果数量"),
    min_score: Optional[float] = Query(None, description="最低相似度分数"),
    doc_ids: Optional[str] = Query(None, description="指定文档ID列表，逗号分隔")
):
    logger.info(f"RAG查询(GET): {question}")

    doc_id_list = None
    if doc_ids:
        doc_id_list = [d.strip() for d in doc_ids.split(",") if d.strip()]

    try:
        rag_service = get_rag_service()
        result = await rag_service.query(
            question=question,
            top_k=top_k,
            min_score=min_score,
            doc_ids=doc_id_list
        )

        results_data = [
            {
                "doc_id": r.doc_id,
                "doc_name": r.doc_name,
                "chunk_index": r.chunk_index,
                "text": r.text,
                "score": r.score,
                "metadata": r.metadata
            }
            for r in result.results
        ]

        response_data = {
            "query": result.query,
            "results": results_data,
            "context": result.context,
            "answer": result.answer,
            "metadata": result.metadata
        }

        if result.debug_info is not None:
            response_data["debug_info"] = {
                "original_query": result.debug_info.original_query,
                "rewritten_query": result.debug_info.rewritten_query,
                "is_rewritten": result.debug_info.is_rewritten,
                "keywords": result.debug_info.keywords,
                "vector_results": result.debug_info.vector_results,
                "keyword_results": result.debug_info.keyword_results,
                "hybrid_results": result.debug_info.hybrid_results,
                "reranked_results": result.debug_info.reranked_results,
                "vector_weight": result.debug_info.vector_weight,
                "keyword_weight": result.debug_info.keyword_weight,
                "feature_status": result.debug_info.feature_status
            }

        return R.ok(data=response_data)

    except Exception as e:
        logger.error(f"RAG查询失败: {e}")
        return R.fail(message=f"查询失败: {str(e)}")


@rag_router.get("/config")
async def get_rag_config():
    logger.info("获取RAG配置")
    return R.ok(data=rag_config.to_dict())


@rag_router.post("/config")
async def update_rag_config(config_update: RAGConfigUpdate):
    logger.info(f"收到更新RAG配置请求: {config_update}")
    
    update_dict = {}
    for key, value in config_update.model_dump(exclude_unset=True).items():
        if value is not None:
            update_dict[key] = value
    
    logger.info(f"更新字段: {update_dict}")
    
    rag_config.update_from_dict(update_dict)
    
    logger.info(f"更新后配置: {rag_config.to_dict()}")
    
    return R.ok(data=rag_config.to_dict(), message="配置已更新")


@rag_router.post("/config/reset")
async def reset_rag_config():
    logger.info("重置RAG配置")
    
    default_config = RAGConfig()
    for key, value in default_config.to_dict().items():
        if hasattr(rag_config, key) and not key.startswith('_'):
            setattr(rag_config, key, value)
    
    logger.info(f"RAG配置已重置: {rag_config.to_dict()}")
    return R.ok(data=rag_config.to_dict(), message="配置已重置为默认值")


@rag_router.get("/documents")
async def list_documents():
    logger.info("获取文档列表")
    rag_service = get_rag_service()
    docs = rag_service.list_documents()
    return R.ok(data={
        "documents": docs,
        "total_docs": len(docs),
        "total_vectors": rag_service.get_vector_count()
    })


@rag_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    logger.info(f"删除文档: {doc_id}")
    rag_service = get_rag_service()
    success = rag_service.delete_document(doc_id)

    if success:
        return R.ok(message=f"文档 {doc_id} 已删除", data={
            "total_docs": rag_service.get_document_count(),
            "total_vectors": rag_service.get_vector_count()
        })
    else:
        return R.not_found(f"文档 {doc_id} 不存在")


@rag_router.delete("/clear")
async def clear_all():
    logger.info("清空所有文档")
    rag_service = get_rag_service()
    rag_service.clear_all()
    return R.ok(message="所有文档已清空", data={
        "total_docs": 0,
        "total_vectors": 0
    })


@rag_router.get("/stats")
async def get_stats():
    rag_service = get_rag_service()
    return R.ok(data={
        "total_docs": rag_service.get_document_count(),
        "total_vectors": rag_service.get_vector_count(),
        "chunk_size": 500,
        "chunk_overlap": 100,
        "vector_store": "json_local",
        "feature_status": rag_config.get_feature_status()
    })
