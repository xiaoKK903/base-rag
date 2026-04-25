import httpx
import hashlib
from typing import List, Optional
from dataclasses import dataclass
from app.config import settings
from app.core.logger import logger


@dataclass
class EmbeddingResult:
    text: str
    vector: List[float]
    model: str
    tokens: int = 0


class EmbeddingService:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.base_url = settings.DASHSCOPE_BASE_URL.rstrip("/")
        self.model = "text-embedding-v4"
        self._client: Optional[httpx.AsyncClient] = None
        self._max_batch_size = 8

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

    async def embed_single(self, text: str) -> EmbeddingResult:
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        if not self.api_key:
            logger.warning("DASHSCOPE_API_KEY not configured, using mock embeddings")
            return self._mock_embeddings(texts)

        url = f"{self.base_url}/embeddings"

        results = []
        batch_size = self._max_batch_size

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            payload = {
                "model": self.model,
                "input": batch,
                "encoding_format": "float",
                "dimensions": 1024
            }

            try:
                logger.info(f"Calling embedding API: {len(batch)} texts, model: {self.model}")
                response = await self.client.post(
                    url,
                    headers=self._generate_request_headers(),
                    json=payload
                )
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"Embedding API error {response.status_code}: {error_text.decode()}")
                    raise Exception(f"Embedding API failed with status {response.status_code}: {error_text.decode()}")
                
                data = response.json()
                logger.info(f"Embedding API response received successfully")

                for j, item in enumerate(data.get("data", [])):
                    embedding = item.get("embedding", [])
                    usage = data.get("usage", {})
                    results.append(EmbeddingResult(
                        text=batch[j],
                        vector=embedding,
                        model=self.model,
                        tokens=usage.get("total_tokens", 0)
                    ))

            except httpx.HTTPStatusError as e:
                logger.error(f"Embedding HTTP status error: {e}")
                raise Exception(f"Embedding API failed: {e}")
            except Exception as e:
                logger.error(f"Embedding API exception: {e}")
                raise

        return results

    def _mock_embeddings(self, texts: List[str]) -> List[EmbeddingResult]:
        results = []
        for text in texts:
            hash_obj = hashlib.sha256(text.encode())
            hash_hex = hash_obj.hexdigest()

            vector = []
            for i in range(0, 128):
                byte_val = int(hash_hex[i % len(hash_hex):i % len(hash_hex) + 2], 16)
                normalized = (byte_val - 128) / 128.0
                vector.append(normalized)

            magnitude = sum(x * x for x in vector) ** 0.5
            if magnitude > 0:
                vector = [x / magnitude for x in vector]

            results.append(EmbeddingResult(
                text=text,
                vector=vector,
                model="mock"
            ))

        return results
