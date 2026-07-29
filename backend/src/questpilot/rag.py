from __future__ import annotations

import hashlib
import math
import re

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload

from questpilot.config import get_settings
from questpilot.models import RagChunk, RagDocument
from questpilot.schemas import RagAnswer, RagCitation


def clean_html(html: str) -> tuple[str, list[tuple[str, str]]]:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "nav", "footer", "form"]):
        node.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else "Mooncell"
    sections: list[tuple[str, str]] = []
    heading = title
    buffer: list[str] = []
    for node in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        if node.name in {"h1", "h2", "h3"}:
            if buffer:
                sections.append((heading, "\n".join(buffer)))
                buffer = []
            heading = node.get_text(" ", strip=True)
        else:
            text = node.get_text(" ", strip=True)
            if text:
                buffer.append(text)
    if buffer:
        sections.append((heading, "\n".join(buffer)))
    return title, sections


def hash_embedding(text: str, dimensions: int = 96) -> list[float]:
    vector = [0.0] * dimensions
    for token in re.findall(r"[\w\u4e00-\u9fff]+", text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % dimensions
        vector[index] += 1 if digest[2] % 2 else -1
    length = math.sqrt(sum(value * value for value in vector)) or 1
    return [value / length for value in vector]


class MooncellIndex:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ingest(
        self,
        *,
        source_url: str,
        html: str,
        revision: str | None = None,
        license_name: str = "CC BY-NC-SA 3.0",
    ) -> RagDocument:
        title, sections = clean_html(html)
        content_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
        document = self.session.scalar(
            select(RagDocument).where(RagDocument.source_url == source_url)
        )
        if document and document.content_sha256 == content_hash:
            return document
        if not document:
            document = RagDocument(
                source_url=source_url,
                title=title,
                revision=revision,
                license_name=license_name,
                content_sha256=content_hash,
            )
            self.session.add(document)
            self.session.flush()
        else:
            document.title = title
            document.revision = revision
            document.content_sha256 = content_hash
            for chunk in self.session.scalars(
                select(RagChunk).where(RagChunk.document_id == document.id)
            ):
                self.session.delete(chunk)
        vector_chunks: list[RagChunk] = []
        for heading, content in sections:
            if not content:
                continue
            chunk = RagChunk(
                document_id=document.id,
                heading=heading,
                content=content,
                token_estimate=max(1, len(content) // 2),
                embedding_json=hash_embedding(f"{heading}\n{content}"),
            )
            self.session.add(chunk)
            vector_chunks.append(chunk)
        if self._pgvector_available():
            self.session.flush()
            for chunk in vector_chunks:
                literal = "[" + ",".join(str(value) for value in chunk.embedding_json) + "]"
                self.session.execute(
                    text(
                        "UPDATE rag_chunks SET embedding_vector = CAST(:vector AS vector) "
                        "WHERE id = :chunk_id"
                    ),
                    {"vector": literal, "chunk_id": chunk.id},
                )
        self.session.commit()
        return document

    def fetch_and_ingest(self, source_url: str, *, timeout_seconds: float = 30) -> RagDocument:
        try:
            response = httpx.get(source_url, timeout=timeout_seconds, follow_redirects=True)
            response.raise_for_status()
        except Exception:
            existing = self.session.scalar(
                select(RagDocument).where(RagDocument.source_url == source_url)
            )
            if existing:
                return existing
            raise
        return self.ingest(
            source_url=source_url,
            html=response.text,
            revision=response.headers.get("last-modified") or response.headers.get("etag"),
        )

    def search(self, query: str, limit: int = 5) -> list[tuple[RagChunk, float]]:
        query_vector = hash_embedding(query)
        terms = set(re.findall(r"[\w\u4e00-\u9fff]+", query.lower()))
        statement = select(RagChunk).options(joinedload(RagChunk.document))
        vector_rank: dict[int, float] = {}
        if self._pgvector_available():
            literal = "[" + ",".join(str(value) for value in query_vector) + "]"
            rows = self.session.execute(
                text(
                    "SELECT id, 1 - (embedding_vector <=> CAST(:vector AS vector)) AS score "
                    "FROM rag_chunks WHERE embedding_vector IS NOT NULL "
                    "ORDER BY embedding_vector <=> CAST(:vector AS vector) LIMIT :limit"
                ),
                {"vector": literal, "limit": max(limit * 4, 20)},
            )
            vector_rank = {int(row.id): float(row.score) for row in rows}
        if self.session.bind and self.session.bind.dialect.name == "postgresql":
            full_text = func.to_tsvector("simple", RagChunk.content).op("@@")(
                func.plainto_tsquery("simple", query)
            )
            matched = list(self.session.scalars(statement.where(full_text)))
            chunks = matched or list(self.session.scalars(statement))
        else:
            chunks = list(self.session.scalars(statement))
        scored = []
        for chunk in chunks:
            vector = chunk.embedding_json or []
            cosine = vector_rank.get(
                chunk.id,
                sum(a * b for a, b in zip(query_vector, vector, strict=False)),
            )
            haystack = f"{chunk.heading} {chunk.content}".lower()
            lexical = sum(1 for term in terms if term in haystack) / max(1, len(terms))
            scored.append((chunk, 0.55 * lexical + 0.45 * cosine))
        return sorted(scored, key=lambda item: (-item[1], item[0].id))[:limit]

    def _pgvector_available(self) -> bool:
        return bool(
            get_settings().pgvector_enabled
            and self.session.bind
            and self.session.bind.dialect.name == "postgresql"
        )

    def answer(self, query: str) -> RagAnswer:
        matches = self.search(query)
        if not matches or matches[0][1] <= 0:
            return RagAnswer(
                answer="当前已验证的 Mooncell 快照中没有足够证据回答这个问题。",
                citations=[],
                route="rag",
            )
        citations = [
            RagCitation(
                source_url=chunk.document.source_url,
                title=chunk.document.title,
                heading=chunk.heading,
                fetched_at=chunk.document.fetched_at,
                excerpt=chunk.content[:220],
            )
            for chunk, _ in matches
        ]
        summary = "；".join(f"{item.heading}：{item.excerpt}" for item in citations[:3])
        return RagAnswer(
            answer=f"根据已验证页面快照：{summary}",
            citations=citations,
            route="rag",
        )
