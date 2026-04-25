from fastapi import APIRouter, UploadFile, File, Form, Query
from typing import List, Optional
from app.core import R, logger
from app.rag.service import get_rag_service

rag_router = APIRouter()


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
async def query_rag(
    question: str = Form(..., description="用户问题"),
    top_k: Optional[int] = Query(None, description="返回结果数量"),
    min_score: Optional[float] = Query(None, description="最低相似度分数"),
    doc_ids: Optional[str] = Query(None, description="指定文档ID列表，逗号分隔")
):
    logger.info(f"RAG查询: {question}")

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

        return R.ok(data={
            "query": result.query,
            "results": results_data,
            "context": result.context,
            "metadata": result.metadata
        })

    except Exception as e:
        logger.error(f"RAG查询失败: {e}")
        return R.fail(message=f"查询失败: {str(e)}")


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
        "chunk_overlap": 100
    })
