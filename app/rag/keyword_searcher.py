import re
import math
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class KeywordSearchResult:
    doc_id: str
    doc_name: str
    chunk_index: int
    text: str
    score: float
    matched_keywords: List[str]
    search_type: str = "keyword"


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        
        self.docs: List[Dict] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        
        self.term_freqs: List[Dict[str, int]] = []
        self.doc_freqs: Dict[str, int] = defaultdict(int)
        self.idf: Dict[str, float] = {}

        self.chunk_to_doc: Dict[int, tuple] = {}

    def _tokenize(self, text: str) -> List[str]:
        text_lower = text.lower()
        
        words = re.findall(r'[a-zA-Z]+|[0-9]+|[\u4e00-\u9fff]', text_lower)
        
        tokens = []
        for word in words:
            if len(word) == 1 and '\u4e00' <= word <= '\u9fff':
                tokens.append(word)
            elif len(word) >= 2:
                tokens.append(word)
        
        if len(words) >= 2:
            for i in range(len(words) - 1):
                if ('\u4e00' <= words[i] <= '\u9fff' and len(words[i]) == 1 and
                    '\u4e00' <= words[i + 1] <= '\u9fff' and len(words[i + 1]) == 1):
                    bigram = words[i] + words[i + 1]
                    tokens.append(bigram)
        
        return tokens

    def add_document(self, doc_id: str, doc_name: str, chunk_index: int, text: str):
        tokens = self._tokenize(text)
        doc_len = len(tokens)
        
        freq = defaultdict(int)
        for token in tokens:
            freq[token] += 1
        
        doc_idx = len(self.docs)
        
        self.docs.append({
            "doc_id": doc_id,
            "doc_name": doc_name,
            "chunk_index": chunk_index,
            "text": text
        })
        self.doc_lengths.append(doc_len)
        self.term_freqs.append(dict(freq))
        
        for term in freq.keys():
            self.doc_freqs[term] += 1
        
        self.chunk_to_doc[(doc_id, chunk_index)] = doc_idx

    def build(self):
        total_docs = len(self.docs)
        if total_docs == 0:
            return
        
        self.avg_doc_length = sum(self.doc_lengths) / total_docs
        
        for term, doc_freq in self.doc_freqs.items():
            self.idf[term] = math.log(1 + (total_docs - doc_freq + 0.5) / (doc_freq + 0.5))

    def search(self, query: str, keywords: List[str] = None, top_k: int = 10) -> List[KeywordSearchResult]:
        if not self.docs:
            return []

        query_tokens = self._tokenize(query)
        if keywords:
            for kw in keywords:
                kw_tokens = self._tokenize(kw)
                query_tokens.extend(kw_tokens)
        
        if not query_tokens:
            return []
        
        scores: Dict[int, float] = defaultdict(float)
        matched_keywords_per_doc: Dict[int, List[str]] = defaultdict(list)
        
        total_docs = len(self.docs)
        
        for term in query_tokens:
            if term not in self.idf:
                continue
            
            idf = self.idf[term]
            
            for doc_idx in range(total_docs):
                if term not in self.term_freqs[doc_idx]:
                    continue
                
                freq = self.term_freqs[doc_idx][term]
                doc_len = self.doc_lengths[doc_idx]
                
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
                
                score = idf * numerator / denominator
                scores[doc_idx] += score
                
                if term not in matched_keywords_per_doc[doc_idx]:
                    matched_keywords_per_doc[doc_idx].append(term)
        
        if not scores:
            return []
        
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        max_score = sorted_docs[0][1] if sorted_docs else 1.0
        
        results = []
        for doc_idx, score in sorted_docs[:top_k]:
            normalized_score = score / max_score if max_score > 0 else 0.0
            
            doc = self.docs[doc_idx]
            results.append(KeywordSearchResult(
                doc_id=doc["doc_id"],
                doc_name=doc["doc_name"],
                chunk_index=doc["chunk_index"],
                text=doc["text"],
                score=normalized_score,
                matched_keywords=matched_keywords_per_doc.get(doc_idx, [])
            ))
        
        return results


class KeywordSearcher:
    def __init__(self):
        self.index = BM25Index()
        self._built = False

    def add_documents(self, documents: List[Dict]):
        for doc in documents:
            self.index.add_document(
                doc_id=doc["doc_id"],
                doc_name=doc["doc_name"],
                chunk_index=doc.get("chunk_index", 0),
                text=doc["text"]
            )

    def build(self):
        self.index.build()
        self._built = True

    def search(self, query: str, keywords: List[str] = None, top_k: int = 10) -> List[KeywordSearchResult]:
        if not self._built:
            self.build()
        
        return self.index.search(query, keywords, top_k)

    def reset(self):
        self.index = BM25Index()
        self._built = False
