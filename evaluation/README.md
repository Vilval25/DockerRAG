# Evaluación

Esta carpeta contiene todo lo necesario para evaluar DevDocsRAG: el banco de preguntas, la
rúbrica, los scripts que generan las respuestas y miden la recuperación, la herramienta de
calificación y los resultados obtenidos.

La evaluación compara las respuestas del mismo modelo sin RAG y con RAG y clasifica si
cada respuesta está fundamentada en la documentación o contiene información inventada.

## Contenido

```text
preguntas_evaluacion_v2.csv     banco de 30 preguntas con respuesta esperada, elementos
                                esenciales y documentos esperados
rubrica_evaluacion.md           rúbrica de calificación con la definición de cada valor
corpus_evaluacion_v2.md         diseño del corpus y del banco de preguntas
evaluate.py                     genera las respuestas sin RAG y con RAG
eval_retrieval.py               métricas automáticas de recuperación
grade.py                        herramienta de calificación (Streamlit)
results/
  evaluacion_dev_resultados.csv          respuestas del conjunto de desarrollo
  evaluacion_test_resultados.csv         respuestas del conjunto de prueba
  evaluacion_test_resultados.meta.json   versión del código, modelo y configuración de la ejecución de prueba
  calificaciones/                        notas de cada evaluador y de consenso
```

Todos los comandos se ejecutan desde la raíz del repositorio, con el índice ya creado
(`python -m src.ingest`) y Ollama en ejecución.

## Conjuntos de preguntas

- **Desarrollo (`dev`, 15 preguntas):** se usa para ajustar el sistema. Cualquier cambio
  se mide aquí.
- **Prueba (`test`, 15 preguntas):** se ejecutó una sola vez, con la configuración ya
  fijada (commit `2c30569`). No se debe ajustar nada a partir de sus preguntas ni de sus
  resultados; una nueva ejecución de prueba debe presentarse como una ejecución nueva.

Además de preguntas directas, aplicadas e integradas, el banco incluye preguntas sin
evidencia en la documentación, preguntas fuera del corpus y preguntas con premisa falsa.

## Métricas de recuperación

```powershell
python -m evaluation.eval_retrieval --split dev
python -m evaluation.eval_retrieval --split test --details   # ranking de cada pregunta
```

Calcula, a partir de los documentos esperados de cada pregunta, el recall, el número de
preguntas con todos sus documentos recuperados y el MRR. Solo comprueba que llegue algún
fragmento del documento correcto; si el fragmento contiene la respuesta se juzga con la
rúbrica.

## Generar respuestas

```powershell
python -m evaluation.evaluate --split dev
python -m evaluation.evaluate --split dev --limit 3 --output evaluation/results/piloto.csv
```

Ejecuta cada pregunta sin RAG y con RAG y guarda las respuestas y los fragmentos
recuperados en `results/evaluacion_<split>_resultados.csv`. Junto al CSV se guarda un
`.meta.json` con el commit, el modelo, la configuración y una huella del corpus, del banco
y de las instrucciones. Haz commit de tus cambios antes de ejecutarlo para que ese registro
sea exacto.

## Calificar

```powershell
streamlit run evaluation/grade.py
```

1. Escribe tu nombre en la barra lateral y elige el archivo de resultados.
2. Para cada pregunta verás la respuesta esperada con sus elementos esenciales, las dos
   respuestas una junto a otra y el texto completo de los fragmentos recuperados, con los
   citados y los de fuentes esperadas señalados.
3. Califica con la [rúbrica](rubrica_evaluacion.md). El icono de ayuda de cada criterio
   muestra la definición de cada valor.
4. Las notas se guardan en `results/calificaciones/<resultados>__<tu_nombre>.csv`, sin
   modificar el archivo de resultados.

Cada evaluador califica por separado. La pestaña **Resumen** muestra las métricas de cada
uno, el acuerdo entre cada par de evaluadores (porcentaje y kappa de Cohen) y las
discrepancias. Las notas finales se guardan con el evaluador `consenso`, que es el que
utiliza el informe.

## Calificaciones incluidas

Las respuestas del conjunto de desarrollo fueron calificadas por dos integrantes del
equipo (`andre`, `gustavo_vila`) y por un modelo de lenguaje (`claude`). La calificación
`consenso` adopta en cada criterio el valor en el que coinciden al menos dos evaluadores;
el único caso sin mayoría se resolvió aplicando la rúbrica. Las notas de `claude` para el
conjunto de prueba son una calificación preliminar que no se revisó manualmente.

## Reproducibilidad

- Las respuestas incluidas se generaron con el corpus descargado el 25 de noviembre de
  2026, que es el que está en `data/documentos/`.
- Si se cambia el corpus o la fragmentación, hay que volver a ejecutar `python -m
  src.ingest`. Las calificaciones hacen referencia a los identificadores de fragmento, así
  que conviene terminar de calificar antes de reindexar.
- La ejecución de prueba se hizo cuando estos scripts estaban en `src/`. Desde entonces
  cambiaron de ubicación y `evaluate.py` adaptó las columnas de calificación del CSV a la
  rúbrica actual, pero el código del sistema (`src/rag.py`, `src/config.py` y
  `src/ingest.py`) no ha cambiado.
