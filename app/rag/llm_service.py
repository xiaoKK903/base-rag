import httpx
from typing import Optional, AsyncGenerator, List
from dataclasses import dataclass
from app.config import settings
from app.core.logger import logger


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens: int = 0


class LLMService:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.base_url = settings.DASHSCOPE_BASE_URL.rstrip("/")
        self.model = "qwen-turbo"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def _generate_request_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _build_prompt(self, question: str, context: str) -> str:
        if not context:
            return question

        prompt = f"""你是一个专业的AI助手，请基于以下检索到的文档内容来回答用户的问题。

【检索到的文档内容】
{context}

【用户问题】
{question}

【回答要求】
1. 请基于检索到的文档内容进行回答，不要编造信息
2. 如果文档中没有相关信息，请明确告知用户
3. 回答要简洁明了，条理清晰
4. 引用的信息要准确"""

        return prompt

    def _build_messages(self, question: str, context: str) -> List[dict]:
        system_prompt = """你是一个专业的AI助手，请基于以下检索到的文档内容来回答用户的问题。

回答要求：
1. 请基于检索到的文档内容进行回答，不要编造信息
2. 如果文档中没有相关信息，请明确告知用户
3. 回答要简洁明了，条理清晰
4. 引用的信息要准确

注意：请直接回答问题，不要重复用户的问题，也不要说"根据检索结果"之类的话。"""

        user_content = question
        if context:
            user_content = f"""【检索到的文档内容】
{context}

【用户问题】
{question}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        return messages

    async def generate(
        self,
        question: str,
        context: str = ""
    ) -> LLMResponse:
        if not self.api_key:
            logger.warning("DASHSCOPE_API_KEY not configured, using mock response")
            return self._mock_generate(question, context)

        url = f"{self.base_url}/chat/completions"

        messages = self._build_messages(question, context)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024
        }

        try:
            logger.info(f"Calling LLM API: {self.model}")
            response = await self.client.post(
                url,
                headers=self._generate_request_headers(),
                json=payload
            )

            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"LLM API error {response.status_code}: {error_text.decode()}")
                return self._fallback_response(question, context)

            data = response.json()
            logger.info(f"LLM API response received successfully")

            choices = data.get("choices", [])
            if not choices:
                logger.error("No choices in LLM response")
                return self._fallback_response(question, context)

            content = choices[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", 0)

            return LLMResponse(
                content=content,
                model=self.model,
                tokens=tokens
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"LLM HTTP status error: {e}")
            return self._fallback_response(question, context)
        except Exception as e:
            logger.error(f"LLM API exception: {e}")
            return self._fallback_response(question, context)

    def _fallback_response(self, question: str, context: str) -> LLMResponse:
        if not context:
            return LLMResponse(
                content="抱歉，当前没有可用的知识库内容，无法回答您的问题。请先上传相关文档。",
                model="fallback",
                tokens=0
            )

        return LLMResponse(
            content="根据检索结果，相关的文档片段已列出。您可以查看这些片段获取需要的信息。",
            model="fallback",
            tokens=0
        )

    def _mock_generate(self, question: str, context: str) -> LLMResponse:
        if not context:
            return LLMResponse(
                content="抱歉，当前没有可用的知识库内容，无法回答您的问题。请先上传相关文档。",
                model="mock",
                tokens=0
            )

        return LLMResponse(
            content="根据检索结果，相关的文档片段已列出。您可以查看这些片段获取需要的信息。",
            model="mock",
            tokens=0
        )
