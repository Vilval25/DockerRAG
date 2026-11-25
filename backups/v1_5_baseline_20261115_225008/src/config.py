"""Configuración central del sistema RAG para Docker y FastAPI."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "data" / "documentos"
DB_DIR = ROOT / "chroma_db"

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
COLLECTION = "docker_fastapi_docs_v1"

# Cantidad final de fragmentos para consultas de un solo dominio.
# Ocho fragmentos permiten conservar evidencias complementarias de una misma
# pregunta (por ejemplo, declaración de un parámetro y su validación).
# Se mantiene configurable mediante la variable de entorno RETRIEVAL_K.
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "8"))

# En consultas sin filtro se seleccionan cinco fragmentos de cada dominio.
INTEGRATED_K_PER_DOMAIN = int(
    os.getenv("INTEGRATED_K_PER_DOMAIN", "5")
)

# Expansión bilingüe de la consulta original mediante Ollama.
QUERY_EXPANSION_ENABLED = (
    os.getenv("QUERY_EXPANSION_ENABLED", "true").lower()
    in {"1", "true", "yes", "si", "sí"}
)

# Candidatos consultados por cada variante de búsqueda y cada dominio.
QUERY_EXPANSION_SEARCH_K = int(
    os.getenv("QUERY_EXPANSION_SEARCH_K", "10")
)

# Constante de Reciprocal Rank Fusion.
RRF_CONSTANT = int(os.getenv("RRF_CONSTANT", "60"))

# Pesos de las consultas utilizadas durante RRF.
# Las consultas específicas tienen prioridad sobre las consultas generales.
RRF_ORIGINAL_QUERY_WEIGHT = float(
    os.getenv("RRF_ORIGINAL_QUERY_WEIGHT", "1.0")
)
RRF_EXPANDED_QUERY_WEIGHT = float(
    os.getenv("RRF_EXPANDED_QUERY_WEIGHT", "0.75")
)
RRF_SPECIFIC_QUERY_WEIGHT = float(
    os.getenv("RRF_SPECIFIC_QUERY_WEIGHT", "0.75")
)
RRF_PRIMARY_QUERY_WEIGHT = float(
    os.getenv("RRF_PRIMARY_QUERY_WEIGHT", "1.25")
)

if min(
    RRF_ORIGINAL_QUERY_WEIGHT,
    RRF_EXPANDED_QUERY_WEIGHT,
    RRF_SPECIFIC_QUERY_WEIGHT,
    RRF_PRIMARY_QUERY_WEIGHT,
) <= 0:
    raise ValueError("Los pesos de las consultas RRF deben ser mayores que cero.")
