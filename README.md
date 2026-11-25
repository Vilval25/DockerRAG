# DevDocsRAG — FastAPI + Docker (Grupo 3)

Prototipo RAG textual para consultas sobre documentación técnica oficial de FastAPI y Docker. Python, LangChain, ChromaDB, embeddings multilingües y un LLM local mediante Ollama.

## Caso de estudio

Asistente para estudiantes y desarrolladores que construyen APIs REST con FastAPI y las empaquetan/despliegan con Docker. El sistema admite preguntas de cada dominio y preguntas integradoras que requieren recuperar información de ambos.

## Requisitos

- Python 3.11 o 3.12 (recomendado 3.11), pip e Internet para descargar las fuentes y modelos.
- Ollama instalado y en ejecución, con `qwen2.5:3b` disponible.
- RAM y espacio suficientes para el LLM, embeddings y ChromaDB.

## Configuración (Windows PowerShell)

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
ollama pull qwen2.5:3b
```

## Pipeline

```powershell
python -m src.download_docs
python -m src.ingest
python -m src.search "¿Cómo funciona Docker Compose?" --domain docker
python -m src.search "¿Cómo funcionan las dependencias?" --domain fastapi
python -m src.search "¿Cómo contenerizar una API FastAPI?"
python -m src.ask "¿Cómo desplegar una API FastAPI con Docker Compose?"
python -m src.ask --base "¿Cómo desplegar una API FastAPI con Docker Compose?"
streamlit run app.py
```

## Corpus

El descargador obtiene 12 páginas oficiales y crea `data/documentos/manifest.json`:

- 6 fuentes Docker: overview, Dockerfile, networking, volumes y Compose.
- 6 fuentes FastAPI: first steps, path parameters, query parameters, request body, dependencies y despliegue en contenedores.

Cada documento conserva `domain`, título, URL y fecha de recopilación. Revisa los Markdown generados y el manifiesto antes de indexar.

## Indexación

`src.ingest` crea fragmentos de 800 caracteres con solapamiento de 150, genera embeddings con `paraphrase-multilingual-MiniLM-L12-v2` e indexa metadatos en ChromaDB. El campo `domain` permite filtrar la búsqueda por `docker` o `fastapi`; si no se aplica filtro, se buscan ambos dominios.

**Importante:** al volver a ejecutar `python -m src.ingest`, se reconstruye la base vectorial local. Este paquete usa una colección nueva (`docker_fastapi_docs_v1`) y reemplaza la carpeta `chroma_db` que exista en este proyecto. Conserva una copia si necesitas preservar el índice anterior.

## Evaluación propuesta

Usar 15 preguntas: 5 sobre FastAPI, 5 sobre Docker y 5 integradoras. Ejecutar cada pregunta con el mismo modelo y parámetros, primero sin RAG y luego con RAG. Evaluar exactitud, fundamentación, relevancia de recuperación y alucinaciones mediante una rúbrica manual. No comparar FastAPI y Docker como tecnologías competidoras: son componentes complementarios del caso de estudio.

## Reproducibilidad y limitaciones

- El corpus se descarga de sitios oficiales en evolución; conservar los Markdown y `manifest.json` para fijar el conjunto exacto usado.
- Revisar el contenido extraído, ya que la estructura HTML puede cambiar.
- El top-k no garantiza que todos los fragmentos sean relevantes.
- La plantilla CSV no contiene resultados experimentales.
- La primera ejecución requiere Internet para descargar páginas y el modelo de embeddings; Ollama requiere tener el modelo local disponible.
