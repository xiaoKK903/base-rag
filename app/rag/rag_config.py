from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from app.config import settings


@dataclass
class RAGConfig:
    enable_query_rewrite: bool = False
    enable_keyword_search: bool = False
    enable_hybrid_search: bool = False
    enable_reranking: bool = False
    enable_debug: bool = False

    vector_weight: float = 0.7
    keyword_weight: float = 0.3

    rerank_top_k: int = 10
    rerank_min_score: float = 0.3

    rewrite_model: str = "qwen-turbo"
    rerank_model: Optional[str] = None

    query_rewrite_prompt: str = """你是一个专业的查询优化助手。请将用户的问题改写为更适合搜索引擎的查询。

要求：
1. 提取核心关键词和实体
2. 保持原问题的语义
3. 如果问题有歧义，请列出可能的多种含义
4. 直接返回改写后的查询，不要解释

用户问题：{question}

改写后的查询："""

    _instance: Optional['RAGConfig'] = None

    @classmethod
    def get_instance(cls) -> 'RAGConfig':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def update_from_dict(self, config_dict: Dict[str, Any]):
        for key, value in config_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_feature_status(self) -> Dict[str, bool]:
        return {
            "query_rewrite": self.enable_query_rewrite,
            "keyword_search": self.enable_keyword_search,
            "hybrid_search": self.enable_hybrid_search,
            "reranking": self.enable_reranking,
            "debug": self.enable_debug,
        }


rag_config = RAGConfig.get_instance()
