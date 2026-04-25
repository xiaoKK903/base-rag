import re
from typing import Optional, List
from dataclasses import dataclass
from app.core.logger import logger
from app.rag.llm_service import LLMService
from app.rag.rag_config import rag_config


@dataclass
class RewriteResult:
    original_query: str
    rewritten_query: str
    keywords: List[str]
    is_rewritten: bool
    model: str = ""


class QueryRewriter:
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()
        self.stop_words = {
            "的", "是", "在", "了", "和", "与", "或", "吗", "呢", "啊", "吧",
            "请", "如何", "怎么", "怎样", "为什么", "为何", "什么", "哪",
            "我", "你", "他", "她", "它", "我们", "你们", "他们",
            "这个", "那个", "这些", "那些", "一个", "一些",
            "能", "可以", "需要", "应该", "必须",
        }

    def _extract_keywords_simple(self, query: str) -> List[str]:
        query_lower = query.lower()
        query_clean = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', query_lower)
        words = query_clean.split()
        
        keywords = []
        for word in words:
            if len(word) >= 2 and word not in self.stop_words:
                keywords.append(word)
        
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', query)
        if len(chinese_chars) >= 2:
            for i in range(len(chinese_chars) - 1):
                bigram = ''.join(chinese_chars[i:i+2])
                if bigram not in self.stop_words and len(bigram) >= 2:
                    if bigram not in keywords:
                        keywords.append(bigram)
        
        return keywords if keywords else words

    async def rewrite(self, query: str) -> RewriteResult:
        if not rag_config.enable_query_rewrite:
            keywords = self._extract_keywords_simple(query)
            return RewriteResult(
                original_query=query,
                rewritten_query=query,
                keywords=keywords,
                is_rewritten=False
            )

        if not rag_config.rewrite_model:
            keywords = self._extract_keywords_simple(query)
            return RewriteResult(
                original_query=query,
                rewritten_query=query,
                keywords=keywords,
                is_rewritten=False
            )

        try:
            prompt = rag_config.query_rewrite_prompt.replace("{question}", query)
            
            messages = [
                {"role": "user", "content": prompt}
            ]

            original_model = self.llm_service.model
            self.llm_service.model = rag_config.rewrite_model

            response = await self.llm_service.generate(query, "")
            
            self.llm_service.model = original_model

            rewritten = response.content.strip() if response.content else query
            
            if not rewritten or len(rewritten) < 2:
                rewritten = query

            keywords = self._extract_keywords_simple(rewritten)
            if not keywords:
                keywords = self._extract_keywords_simple(query)

            logger.info(f"Query rewritten: '{query}' -> '{rewritten}'")
            
            return RewriteResult(
                original_query=query,
                rewritten_query=rewritten,
                keywords=keywords,
                is_rewritten=True,
                model=response.model
            )

        except Exception as e:
            logger.error(f"Query rewrite failed: {e}")
            keywords = self._extract_keywords_simple(query)
            return RewriteResult(
                original_query=query,
                rewritten_query=query,
                keywords=keywords,
                is_rewritten=False
            )
