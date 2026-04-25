import re
from typing import List
from dataclasses import dataclass
from app.config import settings


@dataclass
class DocumentChunk:
    doc_id: str
    doc_name: str
    chunk_index: int
    text: str
    start_pos: int
    end_pos: int


class TextChunker:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def _split_by_paragraph(self, text: str) -> List[str]:
        text = text.replace("\r\n", "\n")
        paragraphs = re.split(r"\n{2,}", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_by_sentence(self, text: str) -> List[str]:
        text = text.replace("\n", " ")
        sentences = re.split(r"(?<=[。！？.!?])\s*", text)
        return [s.strip() for s in sentences if s.strip()]

    def _merge_chunks(self, segments: List[str], max_size: int) -> List[str]:
        if not segments:
            return []

        chunks = []
        current_chunk = ""
        current_size = 0

        for segment in segments:
            segment_len = len(segment)

            if current_size + segment_len <= max_size:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += segment
                current_size = len(current_chunk)
            else:
                if current_chunk:
                    chunks.append(current_chunk)

                if segment_len > max_size:
                    sentences = self._split_by_sentence(segment)
                    temp_chunk = ""
                    temp_size = 0
                    for sent in sentences:
                        sent_len = len(sent)
                        if temp_size + sent_len <= max_size:
                            if temp_chunk:
                                temp_chunk += " "
                            temp_chunk += sent
                            temp_size = len(temp_chunk)
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk)
                            if sent_len > max_size:
                                for i in range(0, sent_len, max_size):
                                    chunks.append(sent[i:i + max_size])
                            else:
                                temp_chunk = sent
                                temp_size = sent_len
                    if temp_chunk:
                        current_chunk = temp_chunk
                        current_size = len(temp_chunk)
                else:
                    current_chunk = segment
                    current_size = segment_len

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        if len(chunks) <= 1 or self.chunk_overlap <= 0:
            return chunks

        result = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                result.append(chunk)
                continue

            prev_chunk = chunks[i - 1]
            overlap_text = prev_chunk[-self.chunk_overlap:] if len(prev_chunk) >= self.chunk_overlap else prev_chunk

            if overlap_text and not chunk.startswith(overlap_text):
                chunk = overlap_text + chunk

            result.append(chunk)

        return result

    def chunk_text(self, text: str, doc_id: str, doc_name: str) -> List[DocumentChunk]:
        paragraphs = self._split_by_paragraph(text)
        chunks = self._merge_chunks(paragraphs, self.chunk_size)
        chunks = self._add_overlap(chunks)

        result = []
        current_pos = 0

        for i, chunk_text in enumerate(chunks):
            start_pos = text.find(chunk_text[:min(100, len(chunk_text))], current_pos)
            if start_pos == -1:
                start_pos = current_pos
            end_pos = start_pos + len(chunk_text)

            chunk = DocumentChunk(
                doc_id=doc_id,
                doc_name=doc_name,
                chunk_index=i,
                text=chunk_text,
                start_pos=start_pos,
                end_pos=end_pos
            )
            result.append(chunk)
            current_pos = end_pos

        return result

    def chunk_file(self, file_path: str, doc_id: str = None, doc_name: str = None) -> List[DocumentChunk]:
        import hashlib

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        if not doc_id:
            doc_id = hashlib.md5(text.encode()).hexdigest()[:16]

        if not doc_name:
            import os
            doc_name = os.path.basename(file_path)

        return self.chunk_text(text, doc_id, doc_name)
