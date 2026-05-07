from __future__ import annotations

from pathlib import Path
from typing import Iterable

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.embeddings import FakeEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.config import get_settings

COLLECTION_NAME = "loan_assistance_knowledge"


def _embeddings() -> FakeEmbeddings:
    # A local deterministic embedding implementation keeps the starter project runnable.
    # Swap this for an OpenAI/OpenRouter-compatible embedding model in production.
    return FakeEmbeddings(size=384)


def get_vectorstore() -> Chroma:
    settings = get_settings()
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=_embeddings(),
        persist_directory=str(settings.vectorstore_dir),
    )


def load_documents(path: Path) -> list[Document]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(str(path)).load()
    if suffix in {".txt", ".md"}:
        return TextLoader(str(path), encoding="utf-8").load()
    raise ValueError(f"Unsupported document type: {suffix}. Use .txt, .md, or .pdf.")


def split_documents(documents: Iterable[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
    return splitter.split_documents(list(documents))


def index_file(path: Path) -> int:
    documents = split_documents(load_documents(path))
    if not documents:
        return 0
    vectorstore = get_vectorstore()
    vectorstore.add_documents(documents)
    return len(documents)


def index_sample_data() -> int:
    settings = get_settings()
    count = 0
    for path in settings.sample_data_dir.glob("*"):
        if path.suffix.lower() in {".txt", ".md", ".pdf"}:
            count += index_file(path)
    return count


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
