"""Carga el corpus mixto, divide documentos e indexa en ChromaDB.

Uso: python -m src.ingest
"""
import json
import shutil
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from .config import DOCS_DIR, DB_DIR, EMBEDDING_MODEL, COLLECTION


def load_documents() -> list[Document]:
    manifest_file = DOCS_DIR / "manifest.json"
    if not manifest_file.exists():
        raise RuntimeError("Falta el manifest. Ejecuta: python -m src.download_docs")

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if not manifest or any(item.get("status") != "ok" for item in manifest):
        raise RuntimeError("El corpus está incompleto; revisa manifest.json y descarga todas las fuentes.")

    domains = {item.get("domain") for item in manifest}
    if not {"docker", "fastapi"}.issubset(domains):
        raise RuntimeError("El corpus debe contener documentos de Docker y FastAPI.")

    documents = []
    for entry in manifest:
        filepath = DOCS_DIR / Path(entry["filename"]).name
        if not filepath.exists():
            raise RuntimeError(f"No existe el documento: {filepath}")
        text = filepath.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError(f"El documento está vacío: {filepath}")
        documents.append(Document(page_content=text, metadata={
            "source": entry["source_url"],
            "title": entry["title"],
            "filename": entry["filename"],
            "domain": entry["domain"],
            "retrieved_at_utc": entry["retrieved_at_utc"],
        }))
    return documents


def make_embeddings():
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


def main():
    documents = load_documents()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"chunk_{index:05d}"

    docker_chunks = sum(chunk.metadata["domain"] == "docker" for chunk in chunks)
    fastapi_chunks = sum(chunk.metadata["domain"] == "fastapi" for chunk in chunks)
    print(f"Documentos: {len(documents)}; fragmentos: {len(chunks)}")
    print(f"Fragmentos Docker: {docker_chunks}; FastAPI: {fastapi_chunks}")

    if DB_DIR.exists():
        shutil.rmtree(DB_DIR)
    db = Chroma(
        collection_name=COLLECTION,
        embedding_function=make_embeddings(),
        persist_directory=str(DB_DIR),
    )
    db.add_documents(chunks, ids=[chunk.metadata["chunk_id"] for chunk in chunks])
    print(f"Índice creado en {DB_DIR}")
    print(f"Fragmentos indexados: {db._collection.count()}")


if __name__ == "__main__":
    main()
