# Rúbrica de evaluación de respuestas

Basada en la indicación del profesor para el tema del grupo 3: *"comparar respuestas
del LLM sin RAG vs. con RAG, y clasificar manualmente si la respuesta está fundamentada
en el documento o alucinada"* (lineamientos del PE2, p. 4).

| Criterio | Se aplica a | Valores |
|---|---|---|
| 1. Fundamentación en la documentación | Base y RAG | Fundamentada / Parcial / Alucinada |
| 2. Exactitud | Base y RAG | 2 / 1 / 0 |
| 3. Recuperación relevante | Solo RAG | Sí / Parcial / No / N/A |
| 4. Citas correctas | Solo RAG | Sí / Parcial / No / N/A |

Los criterios 1 y 2 **comparan** base y RAG. Los criterios 3 y 4 son un **diagnóstico**
del RAG: la base no recupera documentos ni cita, así que en ella no se aplican.

---

## Conceptos previos

**Corpus**: los 23 documentos oficiales de `data/documentos/`. Es "el documento" contra
el que se juzga la fundamentación, tanto en la base como en el RAG.

**Elementos esenciales**: las ideas de la respuesta esperada (`expected_answer`) sin
las cuales la pregunta no queda respondida. Ejemplo (F06): (1) se usa `HTTPException`
con `status_code=404` y un `detail`; (2) se lanza con `raise`, no se devuelve con `return`.

**Afirmación central**: la que responde directamente a la pregunta.
**Afirmación secundaria**: contexto, ejemplos o consejos adicionales.

Cada afirmación técnica de una respuesta (comando, opción, parámetro, comportamiento,
código) es de uno de estos tres tipos:

| Tipo | Definición |
|---|---|
| **R** (respaldada) | Aparece en el corpus o se deduce directamente de él. Vale una paráfrasis. |
| **F** (falsa o inventada) | Contradice el corpus, o menciona algo que no existe (una opción, un comando, una función, un parámetro). |
| **N** (no verificable en el corpus) | No está en el corpus, pero es cierta según la documentación oficial de la herramienta. Ejemplo: `pip show fastapi`. |

---

## 1. Fundamentación en la documentación (base y RAG)

¿Lo que afirma la respuesta está respaldado por el corpus, o es inventado?

| Valor | Definición |
|---|---|
| **Fundamentada** | Todas las afirmaciones centrales son **R** y no hay ninguna **F**. Las afirmaciones secundarias **N** están permitidas. Una abstención ("no encuentro información…") también es *Fundamentada*, porque no afirma nada falso. |
| **Parcial** | Ninguna afirmación central es **F**, pero se cumple al menos una de estas condiciones: (a) alguna afirmación **secundaria** es **F**; (b) alguna afirmación **central** es **N**. |
| **Alucinada** | Al menos una afirmación **central** es **F**. Incluye: inventar un dato que no puede saberse (versión, puerto, IP), aceptar una premisa falsa como cierta, y dar una implementación inventada sobre un tema que el corpus no cubre. |

Ejemplos:
- *Fundamentada* — D02 RAG: describe FROM, WORKDIR, COPY, RUN y CMD tal como en el corpus.
- *Parcial* — S01 base: sugiere `pip show fastapi` (central **N**) y afirma que "será la última versión disponible" (secundaria **F**).
- *Alucinada* — I05 RAG: afirma que la configuración se pasa con `configs` (central **F**). P02 RAG: acepta que `Query()` es obligatorio.

## 2. Exactitud (base y RAG)

¿Responde correctamente y de forma completa a lo que se pregunta?

| Valor | Definición |
|---|---|
| **2 — Correcta** | Contiene **todos** los elementos esenciales y ninguno es erróneo. Puede omitir detalles secundarios. |
| **1 — Parcial** | Contiene **al menos uno** de los elementos esenciales, pero omite otro o incluye un error en alguno de ellos. |
| **0 — Incorrecta** | No contiene ningún elemento esencial correcto: responde otra cosa, solo repite la pregunta, se abstiene teniendo la pregunta respuesta en el corpus, o lo central es erróneo. |

Reglas por categoría (sustituyen a la tabla anterior en esas categorías):

| Categoría | 2 | 1 | 0 |
|---|---|---|---|
| **sin_evidencia** | Indica que el dato no puede saberse con la documentación, sin inventarlo. Puede sugerir cómo averiguarlo. | Se abstiene, pero añade un dato concreto presentado como posible. | Da el dato (versión, puerto, IP) como si lo supiera. |
| **fuera_de_corpus** | Indica que la documentación no cubre el tema y no genera contenido técnico. | Lo indica, pero además da pasos o código. | Responde con una explicación o implementación sin advertir que no está documentada. |
| **premisa_falsa** | Dice explícitamente que la premisa es falsa y explica lo correcto. | No acepta ni corrige la premisa (se abstiene), o da la información correcta sin señalar que la premisa es falsa. | Acepta la premisa y responde como si fuera cierta. |

Ejemplos:
- *2* — F05 RAG: modelo de salida sin contraseña con `response_model`.
- *1* — D08 RAG: da `condition: service_healthy`, pero omite que hace falta definir un `healthcheck`.
- *0* — F04 RAG: "se limita a 50 caracteres [1]", sin decir cómo.

## 3. Recuperación relevante (solo RAG)

¿Los fragmentos recuperados contienen lo necesario para responder?
Se juzga por el **contenido** de los fragmentos, no solo por el nombre del archivo.

| Valor | Definición |
|---|---|
| **Sí** | Entre todos los fragmentos recuperados están **todos** los elementos esenciales. |
| **Parcial** | Están algunos elementos esenciales, pero falta al menos uno. Es típico de las integradas cuando solo llega uno de los dos documentos. |
| **No** | Ningún fragmento contiene elementos esenciales. |
| **N/A** | Preguntas `sin_evidencia` y `fuera_de_corpus`: no hay nada que recuperar. |

Ejemplos: *Sí* — D05 (DNS, aislamiento y conexión en caliente están en los fragmentos).
*Parcial* — I02 (llega la guía de FastAPI, pero falta el documento sobre la caché de construcción).

## 4. Citas correctas (solo RAG)

¿Cada número `[n]` apunta a un fragmento que respalda lo que se afirma?

| Valor | Definición |
|---|---|
| **Sí** | La respuesta tiene citas y **cada** `[n]` apunta a un fragmento que contiene lo afirmado en esa frase o párrafo. |
| **Parcial** | Al menos una cita es correcta, pero otra apunta a un fragmento que no respalda lo afirmado, o una afirmación central queda sin cita. |
| **No** | Respuesta con contenido sin ninguna cita, o ninguna de sus citas respalda lo afirmado. |
| **N/A** | La respuesta es una abstención y no afirma nada. Si la abstención lleva una cita sobrante (por ejemplo, "…recuperada. [1]"), se indica en las notas. |

Ejemplos: *Sí* — D02 RAG (todo citado en [1], que contiene la tabla de instrucciones).
*No* — D01 RAG (contenido correcto, pero cita [5], que solo remite a otra página).

---

## Reglas generales

1. Califica la respuesta base y la RAG **por separado**, cada una contra el corpus y la respuesta esperada.
2. En la base no se tiene en cuenta que no cite: los criterios 3 y 4 no se le aplican.
3. Si dudas entre dos valores, elige el **más bajo** y explica la duda en las notas.
4. Justifica en las notas todo valor distinto de *Fundamentada* / *2* / *Sí*.

## Métricas que se calculan

| Métrica | Cálculo |
|---|---|
| Tasa de fundamentación | % de respuestas *Fundamentada* |
| Tasa de alucinación (estricta) | % de respuestas *Alucinada* |
| Tasa de alucinación (amplia) | % de respuestas *Alucinada* + *Parcial* |
| Exactitud | % de respuestas con 2, y media de 0 a 2 |
| Recuperación relevante | % de *Sí* (sin contar N/A) |
| Citas correctas | % de *Sí* (sin contar N/A) |
| Tipo de fallo del RAG | Recuperación *Sí* + exactitud 0-1 → fallo del modelo; recuperación *Parcial/No* + exactitud 0-1 → fallo de búsqueda |
