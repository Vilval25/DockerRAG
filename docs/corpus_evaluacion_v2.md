# Corpus y banco de preguntas v2

Propuesta para reemplazar el corpus de 13 documentos y el banco de 15 preguntas de la v1.
El banco está en [`results/preguntas_evaluacion_v2.csv`](../results/preguntas_evaluacion_v2.csv).

Todas las URLs y los hechos en los que se basan las respuestas esperadas se comprobaron
en la documentación oficial el **2026-11-25**.

## Principios de diseño

1. **Primero las preguntas, luego el corpus.** Cada pregunta tiene al menos un documento
   que contiene la respuesta de forma explícita (`expected_sources`). No se incluyen
   documentos que no respalden ninguna pregunta.
2. **Solo fuentes oficiales y descargadas por el script.** Ningún documento se escribe a
   mano. El documento 13 de la v1 era un resumen escrito a mano con la URL oficial.
3. **Conjunto de desarrollo y conjunto de prueba.** Las 30 preguntas se dividen en `dev` (15)
   y `test` (15), estratificadas por categoría. Las mejoras del sistema (consultas,
   prompt, parámetros) se ajustan **solo** mirando `dev`. `test` se ejecuta al final
   para medir si la mejora generaliza. Esto evita el sobreajuste de la v1, donde M01, M02
   y las plantillas se diseñaron sobre las mismas preguntas con las que se midió la mejora.
4. **Categorías que prueban la fundamentación, no solo la exactitud.**

| Categoría | Qué mide | dev | test |
|---|---|---:|---:|
| directa | Recuperar y explicar un hecho de un documento | 5 | 4 |
| aplicada | Aplicar lo documentado a un caso concreto | 4 | 5 |
| integrada | Combinar FastAPI y Docker, a menudo de dos documentos | 3 | 3 |
| sin_evidencia | Datos del equipo local que ningún documento puede dar | 1 | 1 |
| fuera_de_corpus | Temas reales que el corpus no cubre: debe abstenerse | 1 | 1 |
| premisa_falsa | La pregunta asume algo falso: debe corregirlo, no seguirle la corriente | 1 | 1 |
| **Total** | | **15** | **15** |

Por dominio: 9 FastAPI, 9 Docker, 6 integradas, 2 sin evidencia, 2 fuera del corpus y 2 de premisa falsa.

## Fuentes (23 documentos)

### FastAPI (10)

| Archivo | URL | Preguntas |
|---|---|---|
| fastapi_path_params.md | https://fastapi.tiangolo.com/tutorial/path-params/ | F01 |
| fastapi_query_params.md | https://fastapi.tiangolo.com/tutorial/query-params/ | F02, P02 |
| fastapi_query_validations.md | https://fastapi.tiangolo.com/tutorial/query-params-str-validations/ | F04, P02 |
| fastapi_request_body.md | https://fastapi.tiangolo.com/tutorial/body/ | F03 |
| fastapi_response_model.md | https://fastapi.tiangolo.com/tutorial/response-model/ | F05 |
| fastapi_handling_errors.md | https://fastapi.tiangolo.com/tutorial/handling-errors/ | F06 |
| fastapi_dependencies.md | https://fastapi.tiangolo.com/tutorial/dependencies/ | F07 |
| fastapi_cli.md | https://fastapi.tiangolo.com/fastapi-cli/ | F08, I03 |
| fastapi_settings.md | https://fastapi.tiangolo.com/advanced/settings/ | F09, I05 |
| fastapi_docker.md | https://fastapi.tiangolo.com/deployment/docker/ | I01, I02, I03 |

### Docker (13)

| Archivo | URL | Preguntas |
|---|---|---|
| docker_what_is_container.md | https://docs.docker.com/learn/content/what-is-a-container/ | D01 |
| docker_write_dockerfile.md | https://docs.docker.com/get-started/docker-concepts/building-images/writing-a-dockerfile/ | D02, D03, P01 |
| docker_build_cache.md | https://docs.docker.com/get-started/docker-concepts/building-images/using-the-build-cache/ | D06, I02 |
| docker_persisting_data.md | https://docs.docker.com/get-started/docker-concepts/running-containers/persisting-container-data/ | I06 |
| docker_storage.md | https://docs.docker.com/engine/storage/ | D04 |
| docker_networking.md | https://docs.docker.com/engine/network/ | D05 |
| docker_bridge.md | https://docs.docker.com/engine/network/drivers/bridge/ | D05 |
| docker_port_publishing.md | https://docs.docker.com/engine/network/port-publishing/ | D03, I03, P01 |
| compose_application_model.md | https://docs.docker.com/compose/intro/compose-application-model/ | D07 |
| compose_networking.md | https://docs.docker.com/compose/how-tos/networking/ | I04 |
| compose_startup_order.md | https://docs.docker.com/compose/how-tos/startup-order/ | D08 |
| compose_env_vars.md | https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/ | D09, I05 |
| compose_volumes.md | https://docs.docker.com/reference/compose-file/volumes/ | I06 |

Cada documento del corpus respalda al menos una pregunta, y cada pregunta con evidencia
tiene al menos un documento.

### Cambios respecto al corpus v1

| v1 | v2 | Motivo |
|---|---|---|
| 01_docker_overview | docker_what_is_container | La URL antigua da **404**: Docker trasladó el contenido a *Docker Learn*. |
| 02_dockerfile | docker_write_dockerfile | Misma URL, pero **el contenido cambió**: ahora es "Write your first Dockerfile" e indica explícitamente que EXPOSE no publica el puerto. |
| 04_volumes (28 KB, NFS/CIFS/backups) | docker_storage + docker_persisting_data | Páginas más cortas y centradas en lo que se pregunta. |
| 07_fastapi_first_steps | (eliminado) | Ninguna pregunta lo necesita: lo que se pregunta sobre `fastapi dev`/`run` está en fastapi_cli. |
| 06_compose_quickstart | (eliminado) | Su ejemplo Flask + Redis hizo que I01 generara `FLASK_APP` y `EXPOSE 5000`. Ninguna pregunta lo necesita. |
| 13_docker_port_publishing (escrito a mano) | docker_port_publishing (descarga real) | El archivo v1 no era la página oficial. |
| — | 10 páginas nuevas (4 FastAPI, 6 Docker) | Respaldan las preguntas nuevas (validaciones, response_model, errores, CLI, settings, caché, bridge, red, arranque, variables y volúmenes en Compose). |

## Cambios necesarios en el código

1. **`src/download_docs.py`**
   - Sustituir `SOURCES` por la lista anterior y usar los nombres de archivo sin número.
   - Eliminar el texto de relleno antes de convertir a Markdown:
     - el aviso "AI coding agents … `uvx library-skills`" de FastAPI;
     - los enlaces `¶` / "Permanent link" de los títulos;
     - "Table of contents" y las anclas `[Título](#ancla)` de Docker.
   - Guardar en el manifiesto `response.url` (ya lo hace) y comprobar que no hubo
     redirección a otra página. Docker está reorganizando su documentación.
2. **`src/add_port_publishing.py`**: eliminarlo.
3. **`src/rag.py`**: quitar las plantillas deterministas (`_build_path_validation_answer`,
   `_build_integrated_evidence_answer`) y las consultas escritas para preguntas concretas
   de la v1. Si se mantiene alguna regla, ajustarla solo con preguntas `dev`.
4. **`src/evaluate.py`**:
   - Añadir `--split dev|test|all`.
   - **No forzar el dominio a partir de la columna `domain` del CSV**: la v1 le pasaba al
     sistema la respuesta correcta sobre el dominio. Evaluar con detección automática
     (`domain=None`) y registrar los dominios detectados.
5. **Volver a indexar** con `python -m src.ingest`. El ID de colección debería cambiar (por ejemplo
   `docker_fastapi_docs_v2`).

## Reproducibilidad

- La documentación oficial cambia: en solo 10 días, dos páginas de Docker del corpus v1
  desaparecieron o cambiaron. **Los Markdown descargados y `manifest.json` deben
  guardarse en git** para fijar el corpus exacto que se evaluó.
- La línea base v1 se puede comparar con `main` (commit `192692e`). Sus resultados usan el
  banco v1, así que la comparación v1 frente a v2 es entre sistemas *y* bancos distintos.
  Si se quiere medir el efecto del nuevo corpus aislado, se puede ejecutar también el
  banco v1 contra el sistema v2.
