from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Iterable

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.config import get_settings

COLLECTION_NAME = "loan_assistance_knowledge"
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


class LocalHashEmbeddings(Embeddings):
    """Small dependency-free embeddings for local RAG demos.

    This is not a production embedding model, but it gives ChromaDB meaningful
    lexical similarity without requiring a paid embeddings API.
    """

    def __init__(self, size: int = 384) -> None:
        self.size = size

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.size
        tokens = re.findall(r"[a-z0-9_]+", text.lower())
        for token in tokens:
            digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
            index = int(digest[:8], 16) % self.size
            sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def _embeddings() -> LocalHashEmbeddings:
    return LocalHashEmbeddings(size=384)


def get_vectorstore() -> Chroma:
    settings = get_settings()
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=_embeddings(),
        persist_directory=str(settings.vectorstore_dir),
    )


def create_embeddings() -> LocalHashEmbeddings:
    return _embeddings()


def load_documents(path: Path) -> list[Document]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        documents = PyPDFLoader(str(path)).load()
    elif suffix in {".txt", ".md"}:
        documents = TextLoader(str(path), encoding="utf-8").load()
    else:
        raise ValueError(f"Unsupported document type: {suffix}. Use .txt, .md, or .pdf.")
    for document in documents:
        document.metadata["source"] = str(path)
        document.metadata["filename"] = path.name
    return documents


def split_documents(documents: Iterable[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
    return splitter.split_documents(list(documents))


def chunk_documents(documents: Iterable[Document]) -> list[Document]:
    return split_documents(documents)


def _chunk_id(document: Document) -> str:
    source = str(document.metadata.get("source", "unknown"))
    page = str(document.metadata.get("page", ""))
    digest = hashlib.sha1(f"{source}:{page}:{document.page_content}".encode("utf-8")).hexdigest()
    return digest


def store_chunks(chunks: list[Document]) -> int:
    if not chunks:
        return 0
    vectorstore = get_vectorstore()
    ids = [_chunk_id(chunk) for chunk in chunks]
    # Refresh existing chunk IDs so repeated indexing is safe during development.
    try:
        vectorstore.delete(ids=ids)
    except Exception:
        pass
    vectorstore.add_documents(chunks, ids=ids)
    return len(chunks)


def index_file(path: Path) -> int:
    documents = split_documents(load_documents(path))
    return store_chunks(documents)


def index_sample_data() -> int:
    settings = get_settings()
    count = 0
    for path in settings.sample_data_dir.glob("*"):
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            count += index_file(path)
    return count


def index_policy_documents() -> int:
    return index_sample_data()


def retrieve_context(question: str, k: int = 4) -> tuple[str, list[dict[str, str]]]:
    vectorstore = get_vectorstore()
    docs = vectorstore.similarity_search(question, k=k)
    context_parts: list[str] = []
    sources: list[dict[str, str]] = []
    for doc in docs:
        source = str(doc.metadata.get("source", "knowledge-base"))
        page = doc.metadata.get("page")
        label = f"{source}" + (f", page {page + 1}" if isinstance(page, int) else "")
        context_parts.append(f"Source: {label}\n{doc.page_content}")
        sources.append({"source": source, "page": str(page + 1) if isinstance(page, int) else ""})
    return "\n\n---\n\n".join(context_parts), sources


def retrieve_relevant_chunks(question: str, k: int = 4) -> list[Document]:
    vectorstore = get_vectorstore()
    return vectorstore.similarity_search(question, k=k)
