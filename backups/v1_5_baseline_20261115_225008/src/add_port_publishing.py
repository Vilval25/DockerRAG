"""Añade e indexa incrementalmente la documentación de publicación de puertos.

Ejecutar desde la raíz del proyecto:
    python -m src.add_port_publishing

El script conserva los documentos y embeddings existentes. Solo incorpora
los fragmentos de 13_docker_port_publishing.md a la colección Chroma actual.
"""
import json
from datetime import datetime, timezone

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import DOCS_DIR, DB_DIR, COLLECTION
from .ingest import make_embeddings


FILENAME = "13_docker_port_publishing.md"
TITLE = "Port publishing and mapping"
SOURCE_URL = "https://docs.docker.com/engine/network/port-publishing/"
DOMAIN = "docker"


def load_manifest(manifest_path):
    if not manifest_path.exists():
        raise RuntimeError(
            "No se encontró data/documentos/manifest.json. "
            "Comprueba que el corpus original esté instalado."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise RuntimeError("El manifest.json no tiene el formato esperado.")

    domains = {item.get("domain") for item in manifest if item.get("status") == "ok"}
    if not {"docker", "fastapi"}.issubset(domains):
        raise RuntimeError(
            "El manifiesto debe contener documentos Docker y FastAPI "
            "con estado 'ok'."
        )

    errors = [item for item in manifest if item.get("status") != "ok"]
    if errors:
        raise RuntimeError(
            "El manifiesto contiene descargas fallidas. Corrige esos errores "
            "antes de continuar para mantener la coherencia del corpus."
        )
    return manifest


def split_document(text, metadata):
    document = Document(page_content=text, metadata=metadata)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents([document])
    if not chunks:
        raise RuntimeError("El documento no produjo fragmentos para indexar.")
    return chunks


def next_chunk_number(existing_ids, existing_metadatas):
    numbers = []
    for item_id, metadata in zip(existing_ids, existing_metadatas):
        value = (metadata or {}).get("chunk_id", item_id)
        if isinstance(value, str) and value.startswith("chunk_"):
            suffix = value.removeprefix("chunk_")
            if suffix.isdigit():
                numbers.append(int(suffix))
    return max(numbers, default=-1) + 1


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = DOCS_DIR / "manifest.json"
    doc_path = DOCS_DIR / FILENAME

    manifest = load_manifest(manifest_path)

    if not doc_path.exists():
        raise RuntimeError(
            f"No se encontró {doc_path}. Descomprime el paquete en la raíz "
            "de DockerRAG y vuelve a ejecutar el comando."
        )

    text = doc_path.read_text(encoding="utf-8").strip()
    if len(text) < 500:
        raise RuntimeError("El documento está vacío o contiene muy poco texto.")

    retrieved_at = datetime.now(timezone.utc).isoformat()
    entry = {
        "filename": FILENAME,
        "title": TITLE,
        "domain": DOMAIN,
        "source_url": SOURCE_URL,
        "retrieved_at_utc": retrieved_at,
        "characters": len(text),
        "status": "ok",
    }

    existing_entry = next(
        (item for item in manifest if item.get("filename") == FILENAME),
        None,
    )
    if existing_entry is None:
        manifest.append(entry)
    else:
        existing_entry.update(entry)

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if not DB_DIR.exists():
        raise RuntimeError(
            "No se encontró chroma_db. El documento quedó registrado en el "
            "manifiesto; ejecuta python -m src.ingest para crear el índice completo."
        )

    vector_store = Chroma(
        collection_name=COLLECTION,
        embedding_function=make_embeddings(),
        persist_directory=str(DB_DIR),
    )

    if vector_store._collection.count() == 0:
        raise RuntimeError(
            "La colección Chroma está vacía. Ejecuta python -m src.ingest "
            "para crear el índice completo."
        )

    chunks = split_document(
        text,
        {
            "source": SOURCE_URL,
            "title": TITLE,
            "filename": FILENAME,
            "domain": DOMAIN,
            "retrieved_at_utc": retrieved_at,
        },
    )

    current = vector_store.get(include=["metadatas"])
    all_ids = current.get("ids", [])
    all_metadatas = current.get("metadatas", []) or []

    # Si el archivo ya estaba indexado, evita duplicarlo. Si quedó una
    # indexación parcial, elimina solo sus fragmentos y vuelve a agregarlos.
    file_ids = [
        item_id
        for item_id, metadata in zip(all_ids, all_metadatas)
        if (metadata or {}).get("filename") == FILENAME
    ]

    if len(file_ids) == len(chunks):
        print(
            f"El documento {FILENAME} ya está indexado "
            f"({len(file_ids)} fragmentos). No se realizaron cambios."
        )
        print(f"Documentos en el manifiesto: {len(manifest)}")
        print(f"Fragmentos en ChromaDB: {vector_store._collection.count()}")
        return

    if file_ids:
        vector_store.delete(ids=file_ids)
        current = vector_store.get(include=["metadatas"])
        all_ids = current.get("ids", [])
        all_metadatas = current.get("metadatas", []) or []

    start_number = next_chunk_number(all_ids, all_metadatas)
    chunk_ids = []
    for index, chunk in enumerate(chunks):
        chunk_id = f"chunk_{start_number + index:05d}"
        chunk.metadata["chunk_id"] = chunk_id
        chunk_ids.append(chunk_id)

    vector_store.add_documents(chunks, ids=chunk_ids)

    print(f"Documento añadido: {FILENAME}")
    print(f"Dominio: {DOMAIN}")
    print(f"Fragmentos nuevos: {len(chunks)}")
    print(f"Identificadores: {chunk_ids[0]} a {chunk_ids[-1]}")
    print(f"Documentos en el manifiesto: {len(manifest)}")
    print(f"Fragmentos totales en ChromaDB: {vector_store._collection.count()}")
    print("No fue necesario volver a indexar los documentos anteriores.")


if __name__ == "__main__":
    main()
