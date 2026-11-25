# Evaluación experimental de DockerRAG

## Archivos incluidos

- `results/preguntas_evaluacion.csv`: banco inicial de 15 preguntas, respuestas de referencia y fuentes esperadas.
- `src/evaluate.py`: ejecuta cada pregunta con el mismo modelo Ollama en dos condiciones: sin RAG y con RAG.

## Instalación

Copia las carpetas `src` y `results` de este paquete dentro de tu proyecto `DockerRAG`, combinando las carpetas y conservando tus archivos existentes.

Asegúrate de que:
- El entorno virtual esté activado.
- Ollama esté en ejecución.
- `qwen2.5:3b` esté descargado.
- El corpus FastAPI + Docker esté descargado e indexado.

## Prueba piloto

Desde la raíz de `DockerRAG`:

```powershell
python -m src.evaluate --limit 2 --output results/piloto.csv
```

Revisa las dos filas y confirma que se guardaron ambas respuestas y las fuentes recuperadas.

## Ejecutar las 15 preguntas

```powershell
python -m src.evaluate
```

El resultado se guardará en `results/evaluacion_resultados.csv`.

Cada pregunta produce dos respuestas:
- `answer_base`: Qwen2.5 3B sin recuperación documental.
- `answer_rag`: Qwen2.5 3B con recuperación documental.

El script no califica automáticamente. El equipo debe revisar las respuestas y completar manualmente:

- `retrieval_relevant`: Sí / Parcial / No.
- `accuracy_base` y `accuracy_rag`: 2 = correcta, 1 = parcialmente correcta, 0 = incorrecta.
- `grounded_base` y `grounded_rag`: 2 = completamente respaldada, 1 = parcialmente respaldada, 0 = sin respaldo.
- `hallucination_base` y `hallucination_rag`: Sí / No.
- `notes`: justificación breve de la calificación.

## Criterio para preguntas sin evidencia

Las preguntas F05, D05 e I05 consultan datos específicos del equipo local que no están en el corpus estático. Una respuesta correcta debe reconocer que la documentación recuperada no permite determinar esos datos. Si el modelo inventa una versión, dirección IP o puerto actual, se registra como alucinación.

## Métricas que se calcularán después

- Exactitud: respuestas correctas / 15.
- Fundamentación: respuestas completamente respaldadas / 15.
- Tasa de alucinación: respuestas con afirmaciones inventadas o no respaldadas / 15.
- Relevancia de recuperación: preguntas en las que se recuperó la documentación necesaria / 15.

Para preguntas integradas, considera la recuperación plenamente relevante cuando aparecen los documentos necesarios para responder las partes esenciales de la pregunta. Si aparece solo una parte, marca Parcial.


## Mejora de trazabilidad (recomendada)

En `src/rag.py`, dentro del diccionario `sources.append({...})` de la función `answer`,
agrega este campo:

```python
"filename": doc.metadata["filename"],
```

Colócalo junto a `title`, `url` y `domain`. Así, el CSV de resultados mostrará el nombre
exacto del archivo original que aportó cada fragmento y será más fácil contrastarlo con
`expected_sources`.
