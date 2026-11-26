# DevDocsRAG — FastAPI + Docker (Grupo 3)

Sistema RAG (*Retrieval-Augmented Generation*) local para responder en español consultas
sobre la documentación oficial de **FastAPI** y **Docker**. Proyecto Equipo N.º 2 de
Sistemas Inteligentes (UNMSM, 2026-2, sección 3).

- **Modelo generador:** Qwen 2.5:3B mediante [Ollama](https://ollama.com), ejecutado en local.
- **Recuperación:** búsqueda híbrida (embeddings multilingües en ChromaDB + BM25) fusionada con RRF.
- **Corpus:** 23 páginas oficiales (13 Docker, 10 FastAPI), 573 fragmentos.
- **Informe:** [`solPE2_Jefferson-Rojas_Juan-Tocto_Andre-Valenzuela_Gustavo-Vila.ipynb`](solPE2_Jefferson-Rojas_Juan-Tocto_Andre-Valenzuela_Gustavo-Vila.ipynb)

## Instalación (Windows PowerShell)

Requisitos: Python 3.11 o 3.12, [Ollama](https://ollama.com/download) y unos 3 GB libres.

```powershell
git clone <url-del-repositorio>
cd DockerRAG
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull qwen2.5:3b
python -m src.ingest      # crea el índice chroma_db/ a partir de data/documentos/
```

El índice (`chroma_db/`) no está en el repositorio: `src.ingest` lo genera en un par de
minutos y, como el corpus sí está versionado, el resultado es idéntico en cualquier equipo
(mismos identificadores de fragmento).

Si ves caracteres extraños en la consola, ejecuta Python en modo UTF-8:
`$env:PYTHONUTF8 = "1"`.

## Uso

```powershell
streamlit run app.py                                         # interfaz web (demo)
python -m src.ask "¿Cómo publico un puerto con Docker?"       # pregunta con RAG
python -m src.ask --base "¿Cómo publico un puerto con Docker?" # mismo modelo sin RAG
python -m src.search "¿Qué hace EXPOSE?"                     # ver qué fragmentos se recuperan
```

## Estructura

```
data/documentos/          corpus descargado (Markdown) + manifest.json
docs/
  corpus_evaluacion_v2.md diseño del corpus y del banco de preguntas
  rubrica_evaluacion.md   rúbrica de calificación (definición de cada valor)
results/
  preguntas_evaluacion_v2.csv            banco de 30 preguntas (dev/test)
  evaluacion_{dev,test}_resultados.csv   respuestas sin RAG y con RAG
  evaluacion_test_resultados.meta.json   con qué versión exacta se generó test
  calificaciones/                        notas por evaluador
src/
  config.py           parámetros (modelos, colección, recuperación, BM25)
  download_docs.py    descarga y limpieza del corpus
  ingest.py           fragmentación e indexación en ChromaDB
  rag.py              detección de dominio, búsqueda híbrida, RRF, prompts, generación
  search.py, ask.py   herramientas de terminal
  evaluate.py         ejecuta el banco sin RAG y con RAG
  eval_retrieval.py   métricas automáticas de recuperación
app.py                interfaz Streamlit
grade.py              herramienta de calificación manual
```

## Evaluación

Sigue el lineamiento del docente: comparar respuestas **sin RAG y con RAG** y clasificar
si están **fundamentadas en la documentación o alucinadas**.

El banco tiene 30 preguntas en dos conjuntos:

- **dev (15):** para ajustar el sistema. Todo cambio se mide aquí.
- **test (15):** se ejecutó **una sola vez** con el sistema congelado (commit `2c30569`).
  No se debe ajustar nada mirando sus preguntas ni sus resultados.

### Calificar

```powershell
streamlit run grade.py
```

1. Escribe tu nombre en la barra lateral y elige el archivo (`dev` o `test`).
2. Para cada pregunta verás la respuesta esperada con sus elementos esenciales, las dos
   respuestas y el texto de los fragmentos recuperados. Califica con la rúbrica
   ([`docs/rubrica_evaluacion.md`](docs/rubrica_evaluacion.md)); el ❔ de cada criterio
   muestra la definición de cada valor.
3. Las notas se guardan en `results/calificaciones/<archivo>__<tu_nombre>.csv`.
4. Dos personas califican por separado; en la pestaña **Resumen** se ve el acuerdo
   (kappa) y las discrepancias. Tras discutirlas, se registran las notas finales con el
   nombre **`consenso`**: son las que usa el informe.

Las notas del evaluador `claude` son una calificación preliminar hecha por un LLM, para
contrastar con las del equipo.

### Ejecutar una nueva evaluación

```powershell
python -m src.eval_retrieval --split dev          # métricas de recuperación (rápido)
python -m src.evaluate --split dev                # respuestas sin RAG y con RAG
```

`evaluate` guarda junto al CSV un `.meta.json` con el commit, el modelo y la configuración.
Haz commit de tus cambios **antes** de ejecutarlo para que el registro sea exacto.
Si cambias el sistema, vuelve a ejecutar `dev`; una nueva ejecución de `test` debe
presentarse como una ejecución nueva, no como un ajuste.

## Reproducibilidad

- El corpus de `data/documentos/` corresponde a la descarga del 2026-11-25. La
  documentación oficial cambia con frecuencia; `python -m src.download_docs` descargaría
  una versión distinta y cambiaría los resultados.
- Tras cambiar el corpus o los parámetros de fragmentación hay que volver a ejecutar
  `python -m src.ingest`. Califica las respuestas **antes** de reindexar: los
  identificadores de fragmento de los resultados antiguos dejarían de corresponder.
